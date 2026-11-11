from pathlib import Path
from ipaddress import ip_address
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from urllib.parse import urlsplit


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parents[2] / '.env', extra='ignore')
    database_url: str = Field(repr=False)
    redis_url: str = Field(default='redis://localhost:6379/0', repr=False)
    jwt_secret: str = Field(repr=False)
    jwt_refresh_secret: str = Field(repr=False)
    cors_origins: list[str] = ['http://localhost:5173', 'http://127.0.0.1:5173']
    environment: str = 'development'
    frontend_url: str = 'http://127.0.0.1:5173'
    mail_backend: str = 'mailpit'
    mail_capture_dir: Path | None = None
    mail_smtp_host: str = '127.0.0.1'
    mail_smtp_port: int = Field(default=1025, ge=1, le=65535)
    mail_smtp_timeout: int = Field(default=10, ge=1, le=60)
    mail_from_email: str = 'no-reply@example.com'
    brevo_api_key: str = Field(default='', repr=False)
    mail_daily_limit: int = Field(default=250, ge=1)
    google_client_id: str = ''
    routing_api_key: str = Field(default='', repr=False)
    # PayHere (Sandbox now, live later: same code, different credentials and mode). Leave empty to hide PayHere.
    payhere_merchant_id: str = ''
    payhere_merchant_secret: str = Field(default='', repr=False)
    payhere_mode: str = 'sandbox'
    # Public HTTPS address of this API (for example an ngrok URL) so PayHere can reach the notify endpoint.
    public_api_url: str = ''
    private_document_root: Path | None = None
    operational_media_root: Path | None = None
    vehicle_photo_root: Path | None = None
    review_audit_root: Path | None = None
    review_database_identity: str | None = None
    review_audit_endpoint: str | None = None
    review_audit_auth_file: Path | None = None

    @field_validator('database_url')
    @classmethod
    def postgres_only(cls, value):
        url = make_url(value)
        if url.drivername != 'postgresql+psycopg' or url.database != 'travelly_dev' or url.username != 'travelly_app':
            raise ValueError('Use postgresql+psycopg, database travelly_dev and user travelly_app.')
        return value

    @model_validator(mode='after')
    def secrets(self):
        if self.mail_backend not in ('capture', 'mailpit', 'brevo'):
            raise ValueError('Choose capture, mailpit or brevo email delivery.')
        if self.mail_backend == 'mailpit':
            host = self.mail_smtp_host.strip().lower().strip('[]')
            try:
                loopback = host == 'localhost' or ip_address(host).is_loopback
            except ValueError:
                loopback = False
            if not loopback:
                raise ValueError('Mailpit SMTP must use a loopback host.')
        origin = urlsplit(self.frontend_url)
        if origin.scheme not in ('http', 'https') or not origin.netloc or origin.query or origin.fragment or origin.username or origin.password or origin.path not in ('', '/'):
            raise ValueError('FRONTEND_URL must be an origin without credentials, query or path.')
        for secret in (self.jwt_secret, self.jwt_refresh_secret):
            if len(secret.encode()) < 32 or secret.startswith('REPLACE_'):
                raise ValueError('Set independent random JWT secrets of at least 32 bytes.')
        if self.payhere_mode not in ('sandbox', 'live'):
            raise ValueError('PAYHERE_MODE must be sandbox or live.')
        if self.jwt_secret == self.jwt_refresh_secret:
            raise ValueError('Access and refresh JWT secrets must be different.')
        if self.environment == 'production':
            if self.mail_backend != 'brevo' or not self.brevo_api_key or origin.scheme != 'https' or self.mail_from_email.endswith('@example.com'):
                raise ValueError('Production requires HTTPS and configured real email delivery.')
            redis = urlsplit(self.redis_url)
            if redis.scheme != 'rediss' or not redis.password:
                raise ValueError('Production Redis requires TLS and authentication.')
            if not self.review_audit_endpoint or not self.review_audit_auth_file:
                raise ValueError('Production review requires the isolated journal writer and its restricted IPC credential.')
        return self


def get_settings():
    return Settings()
