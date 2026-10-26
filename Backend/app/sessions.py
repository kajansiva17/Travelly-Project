import time
import redis
from .errors import ApiError, unauthorized
from .security import digest

# Each mutation is atomic across API workers. No extra PostgreSQL table.
RATE = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""
CREATE = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('HSET', KEYS[1], 'uid', ARGV[1], 'current', ARGV[2], 'exp', ARGV[3], 'revoked', '0', 'created', ARGV[4])
redis.call('EXPIREAT', KEYS[1], ARGV[3])
return 1
"""
ROTATE = """
if redis.call('EXISTS', KEYS[1]) == 0 then return 0 end
if redis.call('HGET', KEYS[1], 'uid') ~= ARGV[1] or redis.call('HGET', KEYS[1], 'revoked') ~= '0' then return 0 end
if redis.call('HGET', KEYS[1], 'current') ~= ARGV[2] then
 redis.call('HSET', KEYS[1], 'revoked', '1'); return -1
end
redis.call('HSET', KEYS[1], 'current', ARGV[3])
return 1
"""
LOGOUT = """
if redis.call('EXISTS', KEYS[1]) == 0 or redis.call('HGET', KEYS[1], 'uid') ~= ARGV[1] then return 0 end
if redis.call('HGET', KEYS[1], 'revoked') == '1' then
 if redis.call('HGET', KEYS[1], 'logout_digest') == ARGV[2] then return 1 end
 return 0
end
if redis.call('HGET', KEYS[1], 'current') ~= ARGV[2] then return 0 end
redis.call('HSET', KEYS[1], 'revoked', '1', 'logout_digest', ARGV[2])
return 1
"""


class SessionStore:
    def __init__(self, url, prefix='travelly:'):
        self.client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3)
        self.prefix = prefix

    def key(self, value):
        return self.prefix + value

    def rate(self, key, limit, seconds):
        count, ttl = self.client.eval(RATE, 1, self.key('limit:' + digest(key)), seconds)
        if count > limit:
            self.limited(ttl)

    def limited(self, ttl):
        raise ApiError(429, 'RATE_LIMITED', 'Too many attempts. Please try again later.', headers={'Retry-After': str(max(1, int(ttl)))})

    def failure_key(self, identifier):
        return self.key('fail:' + digest(identifier))

    def check_lock(self, identifier):
        key = self.key('lock:' + digest(identifier))
        ttl = self.client.ttl(key)
        if ttl > 0:
            self.limited(ttl)

    def failure(self, identifier):
        count, ttl = self.client.eval(RATE, 1, self.failure_key(identifier), 900)
        if count >= 5:
            self.client.set(self.key('lock:' + digest(identifier)), '1', ex=900)
        return count

    def clear_failures(self, identifier):
        self.client.delete(self.failure_key(identifier), self.key('lock:' + digest(identifier)))

    def create(self, sid, uid, token, expires):
        if not self.client.eval(CREATE, 1, self.key('session:' + sid), str(uid), digest(token), expires, int(time.time())):
            raise ApiError(503, 'AUTH_DEPENDENCY_UNAVAILABLE', 'Unable to create a session.')

    def get(self, sid, uid, allow_revoked=False):
        data = self.client.hgetall(self.key('session:' + sid))
        if not data or data.get('uid') != str(uid) or int(data['exp']) <= time.time() or (data.get('revoked') != '0' and not allow_revoked):
            raise unauthorized('SESSION_REVOKED')
        return data

    def rotate(self, sid, uid, old_token, new_token):
        if self.client.eval(ROTATE, 1, self.key('session:' + sid), str(uid), digest(old_token), digest(new_token)) != 1:
            raise unauthorized('INVALID_REFRESH_TOKEN')

    def revoke(self, sid):
        # Only mutate an existing key; never create an immortal revoked record.
        self.client.eval("if redis.call('EXISTS', KEYS[1]) == 1 then redis.call('HSET', KEYS[1], 'revoked', '1') end return 1", 1, self.key('session:' + sid))

    def logout(self, sid, uid, token):
        if self.client.eval(LOGOUT, 1, self.key('session:' + sid), str(uid), digest(token)) != 1:
            raise unauthorized('INVALID_SESSION')
