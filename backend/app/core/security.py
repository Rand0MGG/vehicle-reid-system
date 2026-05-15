from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
algorithm = "HS256"
access_token_expire_minutes = 1440
gallery_image_token_expire_minutes = 10
vehicle_gallery_token_expire_minutes = 10
gallery_image_token_scope = "gallery_image"
vehicle_gallery_token_scope = "vehicle_gallery"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=algorithm)
    return encoded_jwt


def create_gallery_image_token(
    *,
    image_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    return create_access_token(
        {
            "scope": gallery_image_token_scope,
            "image_id": int(image_id),
        },
        expires_delta=expires_delta or timedelta(minutes=gallery_image_token_expire_minutes),
    )


def decode_gallery_image_token(token: str) -> dict:
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[algorithm])
    if payload.get("scope") != gallery_image_token_scope:
        raise JWTError("invalid scope")
    return payload


def create_vehicle_gallery_token(
    *,
    user_id: int,
    vehicle_id: str,
    expires_delta: Optional[timedelta] = None,
):
    normalized_vehicle_id = str(vehicle_id or "").strip()
    if not normalized_vehicle_id:
        raise ValueError("vehicle_id is required")

    return create_access_token(
        {
            "scope": vehicle_gallery_token_scope,
            "uid": int(user_id),
            "vehicle_id": normalized_vehicle_id,
        },
        expires_delta=expires_delta or timedelta(minutes=vehicle_gallery_token_expire_minutes),
    )


def decode_vehicle_gallery_token(token: str) -> dict:
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[algorithm])
    if payload.get("scope") != vehicle_gallery_token_scope:
        raise JWTError("invalid scope")
    return payload
