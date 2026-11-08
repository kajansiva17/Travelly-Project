from pydantic import Field, field_validator
from app.schemas import RequestModel, clean_text, phone_number


class ProfileUpdate(RequestModel):
    version: int = Field(ge=1)
    full_name: str = Field(min_length=1, max_length=150)
    phone_e164: str | None
    profile_image_url: str | None = Field(max_length=1_400_000)

    @field_validator('full_name', mode='before')
    @classmethod
    def name(cls, value):
        return clean_text(value.strip()) if isinstance(value, str) else value

    @field_validator('phone_e164')
    @classmethod
    def phone(cls, value):
        return phone_number(value) if value is not None else None
