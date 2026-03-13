"""Tests for TASK-004: Base HTML templates with Jinja2 and HTMX."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.app.main import app
from src.app.database import Base, get_db
from src.app.models import Organization, User
from src.app.auth import get_password_hash


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create a test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user for authenticated requests."""
    org = Organization(
        name="Test Org",
        abn="12345678901",
        onboarding_completed=1  # Mark as completed for tests
    )
    db_session.add(org)
    db_session.flush()

    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        role="admin",
        organization_id=org.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestBaseTemplate:
    """Tests for base.html template."""

    def test_base_html_loads_tailwind_css(self, client, test_user):
        """Verify base.html loads Tailwind CSS from CDN."""
        # Login first to access a page that uses base.html
        response = client.post(
            "/web/login",
            data={"username": "test@example.com", "password": "testpass123"},
            follow_redirects=True
        )
        assert response.status_code == 200

        # Check that dashboard which extends base.html has Tailwind CSS
        assert "https://cdn.tailwindcss.com" in response.text or "cdn.tailwindcss.com" in response.text

    def test_base_html_loads_htmx(self, client, test_user):
        """Verify base.html loads HTMX from CDN."""
        # Login first
        response = client.post(
            "/web/login",
            data={"username": "test@example.com", "password": "testpass123"}
        )

        # Get dashboard
        response = client.get("/dashboard", follow_redirects=True)
        assert response.status_code == 200
        assert "htmx.org" in response.text

    def test_sidebar_shows_all_navigation_items(self, client, test_user):
        """Verify sidebar shows all required navigation items."""
        # Login first
        response = client.post(
            "/web/login",
            data={"username": "test@example.com", "password": "testpass123"}
        )

        # Get dashboard
        response = client.get("/dashboard", follow_redirects=True)
        assert response.status_code == 200

        # Check all navigation items are present
        navigation_items = [
            "Dashboard",
            "IPP Checklist",
            "Privacy Officer",
            "PIAs",
            "Data Register",
            "Access Requests",
            "Incidents",
            "Settings"
        ]
        for item in navigation_items:
            assert item in response.text, f"Navigation item '{item}' not found in sidebar"

    def test_topbar_shows_user_name_and_logout(self, client, test_user):
        """Verify top bar shows logged-in user name and logout button."""
        # Login first
        response = client.post(
            "/web/login",
            data={"username": "test@example.com", "password": "testpass123"}
        )

        # Get dashboard
        response = client.get("/dashboard", follow_redirects=True)
        assert response.status_code == 200
        assert "Test User" in response.text
        assert "Logout" in response.text


class TestLoginTemplate:
    """Tests for login.html template."""

    def test_login_page_renders(self, client):
        """Verify login.html renders as a standalone page."""
        response = client.get("/web/login")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_login_page_extends_base(self, client):
        """Verify login.html extends base.html."""
        response = client.get("/web/login")
        assert response.status_code == 200
        # Check for Tailwind and HTMX from base.html
        assert "cdn.tailwindcss.com" in response.text
        assert "htmx.org" in response.text

    def test_login_page_has_form(self, client):
        """Verify login page has a login form."""
        response = client.get("/web/login")
        assert response.status_code == 200
        assert "<form" in response.text
        assert 'action="/web/login"' in response.text
        assert 'method="POST"' in response.text
        assert 'name="username"' in response.text
        assert 'name="password"' in response.text


class TestRegisterTemplate:
    """Tests for register.html template."""

    def test_register_page_renders(self, client):
        """Verify register.html renders as a standalone page."""
        response = client.get("/web/register")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_register_page_extends_base(self, client):
        """Verify register.html extends base.html."""
        response = client.get("/web/register")
        assert response.status_code == 200
        # Check for Tailwind and HTMX from base.html
        assert "cdn.tailwindcss.com" in response.text
        assert "htmx.org" in response.text

    def test_register_page_has_form(self, client):
        """Verify register page has a registration form."""
        response = client.get("/web/register")
        assert response.status_code == 200
        assert "<form" in response.text
        assert 'action="/web/register"' in response.text
        assert 'method="POST"' in response.text
        assert 'name="email"' in response.text
        assert 'name="full_name"' in response.text
        assert 'name="org_name"' in response.text
        assert 'name="password"' in response.text
        assert 'name="confirm_password"' in response.text


class TestRootRedirect:
    """Tests for GET / redirect behavior."""

    def test_root_redirects_to_login_when_not_authenticated(self, client):
        """Verify GET / redirects to /login when not authenticated."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/web/login" in response.headers["location"]

    def test_root_redirects_to_dashboard_when_authenticated(self, client, test_user):
        """Verify GET / redirects to /dashboard when authenticated."""
        # Login first
        login_response = client.post(
            "/web/login",
            data={"username": "test@example.com", "password": "testpass123"}
        )

        # Now access root
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers["location"]


class TestJinja2ExtendsBlocks:
    """Tests for Jinja2 extends/blocks pattern."""

    def test_templates_use_extends_pattern(self, client):
        """Verify templates use Jinja2 extends/blocks pattern."""
        # Check login.html
        with open("src/app/templates/login.html", "r") as f:
            login_content = f.read()
            assert '{% extends "base.html" %}' in login_content
            assert "{% block" in login_content

        # Check register.html
        with open("src/app/templates/register.html", "r") as f:
            register_content = f.read()
            assert '{% extends "base.html" %}' in register_content
            assert "{% block" in register_content

    def test_base_template_has_blocks(self, client):
        """Verify base.html defines blocks for child templates."""
        with open("src/app/templates/base.html", "r") as f:
            base_content = f.read()
            # Check for essential blocks
            assert "{% block title %}" in base_content
            assert "{% block content %}" in base_content
            assert "{% endblock %}" in base_content
