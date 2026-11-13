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
    # Reminders job (scripts/send_reminders.py): document expiry warning window in working days (PRD default 5),
    # also used for "maintenance due soon"; email copies are off until real delivery is configured.
    reminder_working_days: int = Field(default=5, ge=1, le=30)
    reminder_email_enabled: bool = False
    # Road alerts (owner decisions 12 Nov 2026): minutes an alert stays up per type, relevance radius, and how many
    # nearby Drivers' answers change its status.
    road_alert_minutes_police_presence: int = Field(default=60, ge=5, le=1440)
    road_alert_minutes_speed_check: int = Field(default=60, ge=5, le=1440)
    road_alert_minutes_accident: int = Field(default=120, ge=5, le=1440)
    road_alert_minutes_road_hazard: int = Field(default=120, ge=5, le=1440)
    road_alert_minutes_roadblock: int = Field(default=180, ge=5, le=1440)
    road_alert_radius_km: int = Field(default=15, ge=1, le=100)
    road_alert_active_after_confirmations: int = Field(default=1, ge=1, le=20)
    road_alert_verified_after_confirmations: int = Field(default=3, ge=1, le=50)
    road_alert_removed_after_denials: int = Field(default=2, ge=1, le=20)
    # Seconds the app listens for the Driver's spoken yes/no after asking "Send a Police alert?"; silence = not sent.
    road_alert_confirm_seconds: int = Field(default=10, ge=3, le=30)
    # Odometer photo proof (owner decision 13 Nov 2026): a live photo plus the typed reading at trip start and finish.
    # Photos are private files (no PRD table), deleted this many days after the trip ends; the numbers stay in trips.
    odometer_photo_required: bool = True
    odometer_photo_root: Path | None = None       # default: <PRIVATE_DOCUMENT_ROOT>/../odometer-photos
    odometer_photo_keep_days: int = Field(default=7, ge=1, le=90)
    odometer_pickup_radius_km: float = Field(default=2.0, ge=0.1, le=50)
    odometer_match_tolerance_km: float = Field(default=1.0, ge=0, le=20)
    odometer_unreadable_tries: int = Field(default=3, ge=1, le=10)
    # Travel Reels (PRD tables 18-19; owner decisions 13 Nov 2026): posts are public at once (Admin can hide), reels up
    # to 60 seconds and 50 MB. Media folder default: <PRIVATE_DOCUMENT_ROOT>/../social-media.
    social_media_root: Path | None = None
    social_reel_max_seconds: int = Field(default=60, ge=5, le=600)
    social_reel_max_mb: int = Field(default=50, ge=5, le=500)
    # Travelly AI (PRD matrix 90-91 smart search; help assistant owner decision 12 Nov 2026). Google AI Studio key;
    # empty = the built-in rules answer instead. The daily cap keeps the free tier from running out; after it the rules
    # answer too.
    gemini_api_key: str = Field(default='', repr=False)
    gemini_model: str = 'gemini-2.5-flash'
    gemini_daily_limit: int = Field(default=200, ge=0, le=100000)
    gemini_timeout_seconds: int = Field(default=8, ge=1, le=60)
    google_client_id: str = ''
    routing_api_key: str = Field(default='', repr=False)
    # HeiGIT shut down api.openrouteservice.org on 2-6 Nov 2026; the same key works on api.heigit.org (no trailing slash).
    routing_base_url: str = 'https://api.heigit.org'
    # PayHere (Sandbox now, live later: same code, different credentials and mode). Leave empty to hide PayHere.
    payhere_merchant_id: str = ''
    payhere_merchant_secret: str = Field(default='', repr=False)
    payhere_mode: str = 'sandbox'
    # PayHere Refund API (Settings > API Keys, permission "Automatic Charging API"); without them refunds stay manual.
    payhere_app_id: str = Field(default='', repr=False)
    payhere_app_secret: str = Field(default='', repr=False)
    # Public HTTPS address of this API (for example an ngrok URL) so PayHere can reach the notify endpoint.
    public_api_url: str = ''
    private_document_root: Path | None = None
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
