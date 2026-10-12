import os, tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import Review, User

client = TestClient(app)


def auth():
    client.post("/auth/register", json={"username": "tester", "password": "secret1"})
    t = client.post("/auth/token", data={"username": "tester", "password": "secret1"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def admin_auth():
    client.post("/auth/register", json={"username": "api-admin", "password": "secret1"})
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username="api-admin").first()
        user.is_admin = True
        db.commit()
    finally:
        db.close()
    t = client.post("/auth/token", data={"username": "api-admin", "password": "secret1"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_requires_auth():
    assert client.get("/reviews").status_code == 401


def test_review_and_insights():
    h = auth()
    assert client.post("/reviews", json={"text": "Great product, love it"}, headers=h).json()["sentiment"] == "positive"
    for t in ["Terrible slow delivery", "Slow shipping, very late", "Broken screen, want refund"]:
        client.post("/reviews", json={"text": t}, headers=h)
    d = client.get("/insights", headers=h).json()
    assert d["total"] == 4
    assert d["sentiment_counts"]["negative"] == 3
    assert d["top_complaints"]


def test_csv_upload():
    h = auth()
    r = client.post("/reviews/upload", files={"file": ("r.csv", b"text\nAmazing\nAwful\n")}, headers=h)
    assert r.json()["imported"] == 2


def test_admin_can_list_and_delete_users():
    client.post("/auth/register", json={"username": "managed-user", "password": "secret1"})
    user_token = client.post("/auth/token", data={"username": "managed-user", "password": "secret1"}).json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    assert client.get("/admin/users", headers=user_headers).status_code == 403
    admin_headers = admin_auth()
    client.post("/reviews", json={"text": "Great product"}, headers=user_headers)

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username="managed-user").first()
        user_id = user.id
    finally:
        db.close()

    listed = client.get("/admin/users", headers=admin_headers)
    assert listed.status_code == 200
    assert next(entry for entry in listed.json() if entry["id"] == user_id)["review_count"] == 1

    deleted = client.delete(f"/admin/users/{user_id}", headers=admin_headers)
    assert deleted.status_code == 200
    assert client.get("/reviews", headers=user_headers).status_code == 401
    db = SessionLocal()
    try:
        assert db.query(Review).filter_by(user_id=user_id).count() == 0
    finally:
        db.close()


def test_admin_cannot_delete_last_admin_or_self():
    admin_headers = admin_auth()
    db = SessionLocal()
    try:
        admin_id = db.query(User).filter_by(username="api-admin").first().id
    finally:
        db.close()

    assert client.delete(f"/admin/users/{admin_id}", headers=admin_headers).status_code == 400
