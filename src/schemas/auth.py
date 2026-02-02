from pydantic import EmailStr

from src.schemas.common import BaseSchema


class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseSchema):
    refresh_token: str


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class RegisterRequest(BaseSchema):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None


class PasswordResetRequest(BaseSchema):
    email: EmailStr


class PasswordReset(BaseSchema):
    token: str
    new_password: str
