"""Test bootstrap: forces a throwaway SQLite DB and offline providers BEFORE
any `app.*` module is imported, since `app.config.settings` and `app.db.engine`
are constructed at import time."""
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='.db')}"
os.environ["OCR_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app)
