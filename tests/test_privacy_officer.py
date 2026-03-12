"""Tests for TASK-006: Privacy Officer management."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date

from src.app.main import app
from src.app.database import Base, get_db
from src.app.models import Organization, User, PrivacyOfficer
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
def test_org(db_session):
    """Create a test organization."""
    org = Organization(name="Test Org", abn="12345678901", industry="Technology")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def admin_user(db_session, test_org):
    """Create an admin user for testing."""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Admin User",
        role="admin",
        organization_id=test_org.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session, test_org):
    """Create a regular (non-admin) user for testing."""
    user = User(
        email="user@example.com",
        hashed_password=get_password_hash("userpass123"),
        full_name="Regular User",
        role="user",
        organization_id=test_org.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def another_user(db_session, test_org):
    """Create another user in the same organization."""
    user = User(
        email="another@example.com",
        hashed_password=get_password_hash("anotherpass123"),
        full_name="Another User",
        role="user",
        organization_id=test_org.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def privacy_officer(db_session, test_org, regular_user):
    """Create a privacy officer for testing."""
    officer = PrivacyOfficer(
        user_id=regular_user.id,
        organization_id=test_org.id,
        designation_date=date.today(),
        contact_phone="+61 8 1234 5678"
    )
    db_session.add(officer)
    db_session.commit()
    db_session.refresh(officer)
    return officer


class TestPrivacyOfficerPageAccess:
    """Tests for accessing the Privacy Officer page."""

    def test_privacy_officer_page_requires_authentication(self, client):
        """Verify that unauthenticated users are redirected to login."""
        response = client.get("/privacy-officer", follow_redirects=False)
        assert response.status_code == 302
        assert "/web/login" in response.headers["location"]

    def test_authenticated_user_can_access_page(self, client, admin_user):
        """Verify that authenticated users can access the page."""
        # Login first
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Access privacy officer page
        response = client.get("/privacy-officer")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_page_shows_designation_prompt_when_no_officer(self, client, admin_user):
        """Verify page shows prompt to designate when no officer exists."""
        # Login
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Access page
        response = client.get("/privacy-officer")
        assert response.status_code == 200
        assert "No Privacy Officer has been designated" in response.text
        assert "Action Required" in response.text

    def test_page_shows_current_officer_details(
        self, client, admin_user, privacy_officer
    ):
        """Verify page shows current officer details when one exists."""
        # Login
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Access page
        response = client.get("/privacy-officer")
        assert response.status_code == 200
        assert "Current Privacy Officer" in response.text
        assert "Regular User" in response.text
        assert "user@example.com" in response.text
        assert "+61 8 1234 5678" in response.text


class TestPrivacyOfficerResponsibilities:
    """Tests for Privacy Officer responsibilities display."""

    def test_page_shows_officer_responsibilities(self, client, admin_user):
        """Verify page displays officer responsibilities."""
        # Login
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Access page
        response = client.get("/privacy-officer")
        assert response.status_code == 200

        # Check for responsibilities
        assert "Privacy Officer Responsibilities" in response.text
        assert "Handle privacy complaints" in response.text
        assert "oversee" in response.text.lower() and "pia" in response.text.lower()
        assert "breach response" in response.text.lower()


class TestDesignatePrivacyOfficer:
    """Tests for designating a Privacy Officer."""

    def test_admin_can_designate_officer(
        self, client, db_session, admin_user, another_user
    ):
        """Verify admin can designate a privacy officer."""
        # Login as admin
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Designate privacy officer
        response = client.post(
            "/api/privacy-officer",
            data={
                "user_id": another_user.id,
                "contact_phone": "+61 8 9999 8888"
            },
            follow_redirects=False
        )

        # Should redirect to privacy officer page
        assert response.status_code == 303
        assert "/privacy-officer" in response.headers["location"]

        # Verify officer was created in database
        officer = db_session.query(PrivacyOfficer).filter(
            PrivacyOfficer.user_id == another_user.id
        ).first()
        assert officer is not None
        assert officer.organization_id == admin_user.organization_id
        assert officer.contact_phone == "+61 8 9999 8888"
        assert officer.designation_date == date.today()

    def test_admin_can_update_existing_officer(
        self, client, db_session, admin_user, privacy_officer, another_user
    ):
        """Verify admin can change the privacy officer."""
        # Login as admin
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Update privacy officer
        response = client.post(
            "/api/privacy-officer",
            data={
                "user_id": another_user.id,
                "contact_phone": "+61 8 7777 6666"
            },
            follow_redirects=False
        )

        assert response.status_code == 303

        # Verify officer was updated (should still be only one)
        officers = db_session.query(PrivacyOfficer).all()
        assert len(officers) == 1
        assert officers[0].user_id == another_user.id
        assert officers[0].contact_phone == "+61 8 7777 6666"

    def test_non_admin_cannot_designate_officer(
        self, client, regular_user, another_user
    ):
        """Verify non-admin users cannot designate privacy officers."""
        # Login as regular user
        client.post(
            "/web/login",
            data={"username": "user@example.com", "password": "userpass123"}
        )

        # Try to designate privacy officer
        response = client.post(
            "/api/privacy-officer",
            data={
                "user_id": another_user.id,
                "contact_phone": "+61 8 9999 8888"
            },
            follow_redirects=False
        )

        # Should return 403 Forbidden
        assert response.status_code == 403

    def test_cannot_designate_nonexistent_user(self, client, admin_user):
        """Verify cannot designate a user that doesn't exist."""
        # Login as admin
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Try to designate non-existent user
        response = client.post(
            "/api/privacy-officer",
            data={
                "user_id": 99999,
                "contact_phone": "+61 8 9999 8888"
            },
            follow_redirects=True
        )

        assert response.status_code == 400
        assert "Selected user not found" in response.text

    def test_cannot_designate_user_from_different_org(
        self, client, db_session, admin_user, test_org
    ):
        """Verify cannot designate a user from a different organization."""
        # Create another organization and user
        other_org = Organization(name="Other Org", abn="98765432109", industry="Finance")
        db_session.add(other_org)
        db_session.commit()
        db_session.refresh(other_org)

        other_user = User(
            email="other@example.com",
            hashed_password=get_password_hash("otherpass123"),
            full_name="Other User",
            role="user",
            organization_id=other_org.id
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        # Login as admin
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Try to designate user from different org
        response = client.post(
            "/api/privacy-officer",
            data={
                "user_id": other_user.id,
                "contact_phone": "+61 8 9999 8888"
            },
            follow_redirects=True
        )

        assert response.status_code == 403
        assert "does not belong to your organization" in response.text

    def test_contact_phone_is_optional(
        self, client, db_session, admin_user, another_user
    ):
        """Verify contact phone is optional when designating officer."""
        # Login as admin
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Designate without phone
        response = client.post(
            "/api/privacy-officer",
            data={"user_id": another_user.id},
            follow_redirects=False
        )

        assert response.status_code == 303

        # Verify officer was created without phone
        officer = db_session.query(PrivacyOfficer).first()
        assert officer is not None
        assert officer.contact_phone is None


class TestPrivacyOfficerFormDisplay:
    """Tests for the designation form display."""

    def test_admin_sees_designation_form(self, client, admin_user, another_user):
        """Verify admin users see the designation form."""
        # Login as admin
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Access page
        response = client.get("/privacy-officer")
        assert response.status_code == 200
        assert "Designate Privacy Officer" in response.text
        assert '<form action="/api/privacy-officer"' in response.text
        assert 'name="user_id"' in response.text
        assert 'name="contact_phone"' in response.text

    def test_non_admin_sees_restriction_message(self, client, regular_user):
        """Verify non-admin users see restriction message instead of form."""
        # Login as regular user
        client.post(
            "/web/login",
            data={"username": "user@example.com", "password": "userpass123"}
        )

        # Access page
        response = client.get("/privacy-officer")
        assert response.status_code == 200
        assert "Only administrators can designate" in response.text
        # Should not have the form
        assert '<form action="/api/privacy-officer"' not in response.text

    def test_form_shows_change_button_when_officer_exists(
        self, client, admin_user, privacy_officer
    ):
        """Verify form shows 'Change' button when officer already exists."""
        # Login as admin
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Access page
        response = client.get("/privacy-officer")
        assert response.status_code == 200
        assert "Change Privacy Officer" in response.text
        assert "Update Privacy Officer" in response.text

    def test_form_shows_org_users_in_dropdown(
        self, client, admin_user, regular_user, another_user
    ):
        """Verify form dropdown includes all organization users."""
        # Login as admin
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        # Access page
        response = client.get("/privacy-officer")
        assert response.status_code == 200

        # Check that users from the organization are in the dropdown
        assert "Admin User" in response.text
        assert "Regular User" in response.text
        assert "Another User" in response.text


class TestPrivacyOfficerTemplateIntegration:
    """Tests for template integration."""

    def test_template_extends_base(self, client, admin_user):
        """Verify template extends base.html."""
        # Login
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        response = client.get("/privacy-officer")
        assert response.status_code == 200

        # Check for base.html elements
        assert "cdn.tailwindcss.com" in response.text
        assert "htmx.org" in response.text
        assert "Privacy Officer" in response.text

    def test_template_shows_pris_act_requirement(self, client, admin_user):
        """Verify template shows PRIS Act requirement notice."""
        # Login
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        response = client.get("/privacy-officer")
        assert response.status_code == 200
        assert "PRIS Act Requirement" in response.text
        assert "Cloud Service Provider" in response.text or "CSP" in response.text

    def test_page_title_is_correct(self, client, admin_user):
        """Verify page title is set correctly."""
        # Login
        client.post(
            "/web/login",
            data={"username": "admin@example.com", "password": "adminpass123"}
        )

        response = client.get("/privacy-officer")
        assert response.status_code == 200
        assert "Privacy Officer" in response.text
