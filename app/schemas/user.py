from datetime import datetime

from pydantic import EmailStr, Field, SecretStr, field_validator

from app.core.config import get_settings
from app.core.constants import UserRole, UserStatus
from app.schemas.base import BaseSchema


class UserRegister(BaseSchema):
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        settings = get_settings()
        domain = settings.allowed_email_domain
        if not v.endswith(f"@{domain}"):
            raise ValueError(f"Only @{domain} email addresses are allowed")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: SecretStr) -> SecretStr:
        password = v.get_secret_value()
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseSchema):
    email: EmailStr
    password: SecretStr


class UserCreate(BaseSchema):
    """Internal schema for creating a user in the database."""

    email: str
    password_hash: str
    role: str = UserRole.USER
    status: str = UserStatus.PENDING


class UserUpdate(BaseSchema):
    """Schema for updating user fields."""

    role: str | None = None
    status: str | None = None
    jira_url: str | None = None
    jira_email: str | None = None
    encrypted_jira_token: str | None = None
    jira_display_name: str | None = None
    jira_account_id: str | None = None


class UserResponse(BaseSchema):
    id: int
    email: str
    role: str
    status: str
    jira_url: str | None = None
    jira_email: str | None = None
    jira_display_name: str | None = None
    jira_account_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
