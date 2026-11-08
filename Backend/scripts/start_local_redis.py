"""Start the existing persistent Windows development Redis, without a visible window."""
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))
from app.core.config import get_settings


def cygwin_path(path):
    if len(path.drive) != 2 or path.drive[1] != ':':
        raise RuntimeError('The bundled local Redis requires a Windows drive path.')
    return '/cygdrive/' + path.drive[0].lower() + '/' + '/'.join(path.parts[1:])


def main():
    endpoint = urlsplit(get_settings().redis_url)
    if endpoint.hostname not in ('localhost', '127.0.0.1', '::1') or (endpoint.port or 6379) != 6379:
        raise RuntimeError('This helper supports only configured loopback Redis on port 6379.')
    connection = redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=0.5,
                                     socket_timeout=0.5, retry=Retry(NoBackoff(), 0))

    def ready():
        try:
            return connection.ping()
        except redis.ConnectionError:
            return False
        except redis.TimeoutError:
            return False

    if ready():
        print('Local Redis is already ready. No process was started.')
        return
    executable = ROOT / '.tools/redis/Redis-8.10.2-Windows-x64-cygwin/redis-server.exe'
    config = ROOT / '.tools/redis-dev.conf'
    data = ROOT / '.tools/redis-data'
    if not executable.is_file() or not config.is_file() or not data.is_dir():
        raise RuntimeError('Missing local Redis executable, configuration or existing data. See README.md.')
    # Reuse the original AOF directory. Never clear keys or replace persistent data.
    with (ROOT / '.tools/redis-stdout.log').open('a') as stdout, (ROOT / '.tools/redis-stderr.log').open('a') as stderr:
        process = subprocess.Popen([str(executable), cygwin_path(config), '--dir', cygwin_path(data)],
                                   cwd=ROOT, stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(20):
        time.sleep(0.3)
        if ready():
            print('Local Redis is ready. Retry login.')
            return
        if process.poll() is not None:
            break
    raise RuntimeError('Redis did not become ready. Check .tools/redis-stdout.log and redis-stderr.log. '
                       'If the existing AOF reports Permission denied in a sandbox, run this helper from '
                       'your normal terminal. Do not delete data or disable persistence.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, redis.RedisError, OSError):
        # Do not print dependency exception text, which may include credentials.
        print('Local Redis could not start. Check local setup and .tools/redis-stdout.log / redis-stderr.log. '
              'Run from a normal terminal if the existing AOF is not writable from the sandbox.', file=sys.stderr)
        sys.exit(1)
