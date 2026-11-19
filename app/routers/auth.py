from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import AppUser
from app.schemas.auth import LoginRequest, TokenResponse, UserRegisterRequest
from app.utils.security import (
    create_access_token,
    get_optional_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(AppUser)
        .filter(AppUser.username == payload.username)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username sudah terdaftar",
        )

    user = AppUser(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        nim=payload.nim,
        nidn=payload.nidn,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "nim": user.nim,
        "nidn": user.nidn,
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(AppUser)
        .filter(AppUser.username == payload.username)
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun pengguna tidak aktif",
        )

    token = create_access_token(
        {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "nim": user.nim,
            "nidn": user.nidn,
        }
    )
    return TokenResponse(
        access_token=token,
        username=user.username,
        role=user.role,
        nim=user.nim,
        nidn=user.nidn,
    )


@router.get("/me")
def get_me(current_user: dict = Depends(get_optional_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan",
        )
    return current_user
