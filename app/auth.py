import os, hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .db import get_db
from .models import User

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGO = "HS256"
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")


def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${h}"


def verify_password(pw: str, stored: str) -> bool:
    salt, h = stored.split("$")
    check = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(check, h)


def create_token(username: str, minutes: int = 60) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": username, "exp": exp}, SECRET_KEY, algorithm=ALGO)


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        username = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def current_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Admin privileges required")
    return user
