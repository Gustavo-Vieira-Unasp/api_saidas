from datetime import datetime

from pydantic import BaseModel, ConfigDict

# Access profiles offered by the UNASP pensionato form.
DEFAULT_PROFILE = "Aluno Graduação"


class UserCreate(BaseModel):
    ra: str
    password: str
    profile: str = DEFAULT_PROFILE
    full_name: str | None = None


class ProfileUpdate(BaseModel):
    profile: str


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ra: str
    full_name: str | None = None
    has_unasp_credentials: bool
    unasp_profile: str | None = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
