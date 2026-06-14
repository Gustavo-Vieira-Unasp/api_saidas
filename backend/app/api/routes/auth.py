from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    encrypt_secret,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import PasswordUpdate, ProfileUpdate, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(
    request: Request,
    data: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    existing = db.scalar(select(User).where(User.ra == data.ra))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="RA já cadastrado"
        )
    # The single password is hashed for platform login and encrypted for the
    # UNASP automation, so registration is enough to start sending exits.
    user = User(
        ra=data.ra,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        unasp_username=data.ra,
        unasp_password_enc=encrypt_secret(data.password),
        unasp_profile=data.profile,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    # OAuth2 form sends the RA in the `username` field.
    user = db.scalar(select(User).where(User.ra == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="RA ou senha incorretos",
        )
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/me/profile", response_model=UserOut)
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    current_user.unasp_profile = data.profile
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password", response_model=UserOut)
def update_password(
    data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta",
        )
    current_user.hashed_password = hash_password(data.new_password)
    current_user.unasp_password_enc = encrypt_secret(data.new_password)
    db.commit()
    db.refresh(current_user)
    return current_user
