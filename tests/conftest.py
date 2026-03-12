"""Pytest configuration and fixtures for the WA PRIS Act Compliance Portal."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.main import app
from src.app.database import Base, get_db
from src.app.models import Organization, User
from src.app.auth import get_password_hash

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """
    Create a test database session.

    Yields:
        Session: A test database session
    """
    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(bind=engine)
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db):
    """
    Create a test client for the FastAPI application.

    Args:
        db: Test database session

    Yields:
        TestClient: A test client for making requests to the application
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_org(db):
    """
    Create a test organization.

    Args:
        db: Test database session

    Returns:
        Organization: A test organization
    """
    org = Organization(
        name="Test Organization",
        abn="12345678901",
        industry="Technology"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def test_user(db, test_org):
    """
    Create a test user.

    Args:
        db: Test database session
        test_org: Test organization

    Returns:
        User: A test user
    """
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role="admin",
        organization_id=test_org.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
