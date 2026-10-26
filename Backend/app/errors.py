class ApiError(Exception):
    def __init__(self, status, code, message, fields=None, headers=None):
        self.status, self.code, self.message = status, code, message
        self.fields, self.headers = fields or [], headers or {}


def unauthorized(code='UNAUTHENTICATED'):
    return ApiError(401, code, 'Authentication credentials are invalid or unavailable.', headers={'WWW-Authenticate': 'Bearer'})
