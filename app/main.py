from datetime import datetime
import io
import os
from collections import defaultdict
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from . import nlp
from .auth import hash_password, verify_password, create_token, current_user, current_admin
from .db import SessionLocal, get_db, initialize_database
from .models import User, Review

initialize_database()
app = FastAPI(title="ReviewPulse", description="Customer review intelligence API", version="1.0.0")


def _bootstrap_admin():
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not username and not password:
        return
    if not username or not password or len(username) < 3 or len(username) > 50 or len(password) < 12:
        raise RuntimeError("Set ADMIN_USERNAME (3-50 characters) and ADMIN_PASSWORD (at least 12 characters)")

    db = SessionLocal()
    try:
        admin = db.query(User).filter_by(username=username).first()
        if admin is None:
            db.add(User(username=username, password_hash=hash_password(password), is_admin=True))
            db.commit()
        elif not admin.is_admin:
            raise RuntimeError("ADMIN_USERNAME belongs to a non-admin account; choose a different username")
    finally:
        db.close()


_bootstrap_admin()


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)


class ReviewIn(BaseModel):
    text: str = Field(min_length=1)


def _save(db: Session, user: User, text: str, created_at=None) -> Review:
    label, score = nlp.analyze(text)
    r = Review(user_id=user.id, text=text, sentiment=label, score=score,
               created_at=created_at or datetime.utcnow())
    db.add(r)
    return r


def _out(r: Review) -> dict:
    return {"id": r.id, "text": r.text, "sentiment": r.sentiment, "score": r.score, "created_at": r.created_at}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", status_code=201)
def register(c: Credentials, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=c.username).first():
        raise HTTPException(409, "Username already taken")
    db.add(User(username=c.username, password_hash=hash_password(c.password)))
    db.commit()
    return {"message": "registered"}


@app.post("/auth/token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.query(User).filter_by(username=form.username).first()
    if not u or not verify_password(form.password, u.password_hash):
        raise HTTPException(401, "Wrong username or password")
    return {"access_token": create_token(u.username), "token_type": "bearer"}


@app.post("/reviews", status_code=201)
def add_review(body: ReviewIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    r = _save(db, user, body.text)
    db.commit()
    db.refresh(r)
    return _out(r)


@app.post("/reviews/upload", status_code=201)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    df = pd.read_csv(io.BytesIO(await file.read()))
    if "text" not in df.columns:
        raise HTTPException(400, "CSV must contain a 'text' column")
    dates = pd.to_datetime(df["date"], errors="coerce") if "date" in df.columns else None
    rows = df.dropna(subset=["text"])
    for i, row in rows.iterrows():
        ts = dates[i].to_pydatetime() if dates is not None and pd.notna(dates[i]) else None
        _save(db, user, str(row["text"]), ts)
    db.commit()
    return {"imported": len(rows)}


@app.get("/reviews")
def list_reviews(sentiment: str | None = None, limit: int = 50, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = db.query(Review).filter_by(user_id=user.id)
    if sentiment:
        q = q.filter_by(sentiment=sentiment)
    return [_out(r) for r in q.order_by(Review.id.desc()).limit(min(limit, 500))]


@app.get("/insights")
def insights(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Review).filter_by(user_id=user.id).all()
    totals = defaultdict(int)
    trend = defaultdict(lambda: defaultdict(int))
    for r in rows:
        totals[r.sentiment] += 1
        trend[r.created_at.date().isoformat()][r.sentiment] += 1
    negatives = [r.text for r in rows if r.sentiment == "negative"]
    return {
        "total": len(rows),
        "sentiment_counts": dict(totals),
        "trend": [{"date": d, **v} for d, v in sorted(trend.items())],
        "top_complaints": nlp.cluster_complaints(negatives),
    }


@app.get("/admin/users")
def list_users(db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    users = (
        db.query(User.id, User.username, User.is_admin, func.count(Review.id).label("review_count"))
        .outerjoin(Review, Review.user_id == User.id)
        .group_by(User.id, User.username, User.is_admin)
        .order_by(User.id)
        .all()
    )
    return [
        {"id": user.id, "username": user.username, "is_admin": user.is_admin, "review_count": user.review_count}
        for user in users
    ]


@app.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(current_admin)):
    user = db.query(User).filter_by(id=user_id).first()
    if user is None:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "You cannot delete your own admin account")
    if user.is_admin and db.query(User).filter_by(is_admin=True).count() <= 1:
        raise HTTPException(409, "Cannot delete the last admin account")

    db.query(Review).filter_by(user_id=user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
