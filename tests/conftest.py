import os
import sys

# Point the app at a throwaway SQLite database before any app module is imported.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")
os.environ.setdefault("SECRET_KEY", "test-secret")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

import database as db  # noqa: E402
from models import Base  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Give every test an empty in-memory database with categories, topics and problems."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db.Session.configure(bind=engine)
    db.seed_initial_data()
    db.import_problems()
    yield
    engine.dispose()
