import os

os.environ["DATABASE_URL"] = "sqlite:///./test_smarter.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.models import User
from app.services.security import hash_password


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def users():
    with SessionLocal() as db:
        records = [
            User(email="admin@example.com", full_name="Admin", password_hash=hash_password("AdminPass123!"), role="ADMIN"),
            User(email="nurse@example.com", full_name="Nurse", password_hash=hash_password("NursePass123!"), role="TRIAGE_NURSE"),
            User(email="authority@example.com", full_name="Authority", password_hash=hash_password("AuthorityPass123!"), role="HEALTH_AUTHORITY"),
        ]
        db.add_all(records)
        db.commit()
        return records