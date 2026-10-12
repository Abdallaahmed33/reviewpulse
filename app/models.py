from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, Text
from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    text = Column(Text, nullable=False)
    sentiment = Column(String(10), nullable=False)  # positive | negative | neutral
    score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
