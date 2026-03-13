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

    def test_root_shows_landing_page_when_not_authenticated(self, client):
        """Verify GET / shows landing page when not authenticated."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 200
        assert "PRIS Act Compliance Made Simple" in response.text
        assert "Help your business comply with WA's new privacy law before July 2026" in response.text

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


class TestLandingPage:
    """Tests for TASK-018: Public landing page."""

    def test_landing_page_shows_when_not_authenticated(self, client):
        """Verify GET / shows landing page when not authenticated."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "PRIS Act Compliance Made Simple" in response.text

    def test_hero_section_has_headline_and_cta(self, client):
        """Verify hero section has headline and CTA button."""
        response = client.get("/")
        assert response.status_code == 200
        # Check headline
        assert "PRIS Act Compliance Made Simple" in response.text
        # Check subheadline
        assert "Help your business comply with WA's new privacy law before July 2026" in response.text
        # Check CTA button linking to register
        assert "/web/register" in response.text
        assert "Start Your Free Trial" in response.text or "Get Started" in response.text

    def test_feature_highlights_describe_six_features(self, client):
        """Verify feature highlights section describes 6 key features."""
        response = client.get("/")
        assert response.status_code == 200

        # Check for all 6 features
        features = [
            "IPP Compliance Checklist",
            "Privacy Officer Management",
            "Privacy Impact Assessments",
            "Personal Information Register",
            "Access Request Tracking",
            "Breach Incident Logger"
        ]

        for feature in features:
            assert feature in response.text, f"Feature '{feature}' not found in landing page"

    def test_pricing_section_shows_two_tiers(self, client):
        """Verify pricing section shows two tiers."""
        response = client.get("/")
        assert response.status_code == 200

        # Check for pricing tiers
        assert "$99" in response.text  # Starter tier
        assert "$199" in response.text  # Professional tier

        # Check for tier descriptions
        assert "Up to 5 users" in response.text or "5 users" in response.text
        assert "Unlimited users" in response.text

    def test_faq_section_answers_four_questions(self, client):
        """Verify FAQ section answers 4 common questions."""
        response = client.get("/")
        assert response.status_code == 200

        # Check for all 4 FAQ questions
        questions = [
            "What is the PRIS Act?",
            "Who needs to comply?",
            "What happens if I don't comply?",
            "When does it take effect?"
        ]

        for question in questions:
            assert question in response.text, f"FAQ question '{question}' not found in landing page"

        # Check for some answer content
        assert "Privacy and Responsible Information Sharing" in response.text
        assert "Community Service Providers" in response.text
        assert "July 2026" in response.text

    def test_cta_links_to_register(self, client):
        """Verify CTA links to /register."""
        response = client.get("/")
        assert response.status_code == 200

        # Check that multiple CTAs link to register
        assert "/web/register" in response.text
        # Should have multiple CTAs throughout the page
        assert response.text.count("/web/register") >= 3, "Should have at least 3 links to register page"
