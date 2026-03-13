"""Tests for Role-Based Access Control (RBAC)."""

import pytest
from src.app.models import Organization, User, UserRole
from src.app.auth import get_password_hash, create_access_token


@pytest.fixture
def test_org(db):
    """Create a test organization."""
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
def admin_user(db, test_org):
    """Create an admin user."""
    user = User(
        email="admin@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        organization_id=test_org.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def privacy_officer_user(db, test_org):
    """Create a privacy officer user."""
    user = User(
        email="po@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Privacy Officer",
        role=UserRole.PRIVACY_OFFICER.value,
        organization_id=test_org.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def staff_user(db, test_org):
    """Create a staff user."""
    user = User(
        email="staff@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Staff User",
        role=UserRole.STAFF.value,
        organization_id=test_org.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    """Create an authentication token for admin user."""
    return create_access_token(data={"sub": admin_user.email})


@pytest.fixture
def po_token(privacy_officer_user):
    """Create an authentication token for privacy officer user."""
    return create_access_token(data={"sub": privacy_officer_user.email})


@pytest.fixture
def staff_token(staff_user):
    """Create an authentication token for staff user."""
    return create_access_token(data={"sub": staff_user.email})


class TestUserInvitation:
    """Test user invitation functionality."""

    def test_admin_can_invite_user(self, client, admin_token):
        """Admin can invite new users."""
        response = client.post(
            "/auth/users/invite",
            json={
                "email": "newuser@test.com",
                "role": "staff",
                "full_name": "New User"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "staff"
        assert data["full_name"] == "New User"

    def test_privacy_officer_cannot_invite_user(self, client, po_token):
        """Privacy Officer cannot invite users."""
        response = client.post(
            "/auth/users/invite",
            json={
                "email": "newuser2@test.com",
                "role": "staff",
                "full_name": "Another User"
            },
            headers={"Authorization": f"Bearer {po_token}"}
        )
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_staff_cannot_invite_user(self, client, staff_token):
        """Staff cannot invite users."""
        response = client.post(
            "/auth/users/invite",
            json={
                "email": "newuser3@test.com",
                "role": "staff",
                "full_name": "Yet Another User"
            },
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_cannot_invite_duplicate_email(self, client, admin_token, staff_user):
        """Cannot invite user with existing email."""
        response = client.post(
            "/auth/users/invite",
            json={
                "email": staff_user.email,
                "role": "staff",
                "full_name": "Duplicate User"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_admin_can_invite_admin(self, client, admin_token):
        """Admin can invite other admins."""
        response = client.post(
            "/auth/users/invite",
            json={
                "email": "admin2@test.com",
                "role": "admin",
                "full_name": "Second Admin"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "admin"

    def test_admin_can_invite_privacy_officer(self, client, admin_token):
        """Admin can invite privacy officers."""
        response = client.post(
            "/auth/users/invite",
            json={
                "email": "po2@test.com",
                "role": "privacy_officer",
                "full_name": "Second PO"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "privacy_officer"


class TestTeamManagement:
    """Test team management functionality."""

    def test_get_team_members(self, client, admin_token, admin_user, privacy_officer_user, staff_user):
        """Can retrieve all team members."""
        response = client.get(
            "/auth/users/team",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        emails = [user["email"] for user in data]
        assert admin_user.email in emails
        assert privacy_officer_user.email in emails
        assert staff_user.email in emails

    def test_team_members_only_from_same_org(self, client, admin_token, db):
        """Team members list only shows users from same organization."""
        # Create another organization with a user
        other_org = Organization(
            name="Other Organization",
            abn="99999999999",
            industry="Finance"
        )
        db.add(other_org)
        db.commit()

        other_user = User(
            email="other@test.com",
            hashed_password=get_password_hash("password123"),
            full_name="Other User",
            role=UserRole.ADMIN.value,
            organization_id=other_org.id
        )
        db.add(other_user)
        db.commit()

        response = client.get(
            "/auth/users/team",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        emails = [user["email"] for user in data]
        assert "other@test.com" not in emails

    def test_team_page_requires_authentication(self, client):
        """Team management page requires authentication."""
        response = client.get("/settings/team", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/web/login"

    def test_admin_can_access_team_page(self, client, admin_token):
        """Admin can access team management page."""
        client.cookies.set("access_token", admin_token)
        response = client.get("/settings/team")
        assert response.status_code == 200
        assert "Team Management" in response.text

    def test_privacy_officer_can_access_team_page(self, client, po_token):
        """Privacy Officer can access team management page."""
        client.cookies.set("access_token", po_token)
        response = client.get("/settings/team")
        assert response.status_code == 200
        assert "Team Management" in response.text

    def test_staff_can_access_team_page(self, client, staff_token):
        """Staff can access team management page."""
        client.cookies.set("access_token", staff_token)
        response = client.get("/settings/team")
        assert response.status_code == 200
        assert "Team Management" in response.text


class TestDashboardAccess:
    """Test dashboard access for different roles."""

    def test_admin_can_access_dashboard(self, client, admin_token):
        """Admin has full access to dashboard."""
        client.cookies.set("access_token", admin_token)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Dashboard" in response.text

    def test_privacy_officer_can_access_dashboard(self, client, po_token):
        """Privacy Officer can access dashboard."""
        client.cookies.set("access_token", po_token)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Dashboard" in response.text

    def test_staff_can_access_dashboard(self, client, staff_token):
        """Staff has read-only access to dashboard."""
        client.cookies.set("access_token", staff_token)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Dashboard" in response.text


class TestPIAAccess:
    """Test PIA access for different roles."""

    def test_admin_can_create_pia(self, client, admin_token):
        """Admin can create PIAs."""
        client.cookies.set("access_token", admin_token)
        response = client.get("/pias/new")
        assert response.status_code == 200

    def test_privacy_officer_can_create_pia(self, client, po_token):
        """Privacy Officer can create PIAs."""
        client.cookies.set("access_token", po_token)
        response = client.get("/pias/new")
        assert response.status_code == 200

    def test_admin_can_view_pias(self, client, admin_token):
        """Admin can view PIAs."""
        client.cookies.set("access_token", admin_token)
        response = client.get("/pias")
        assert response.status_code == 200

    def test_privacy_officer_can_view_pias(self, client, po_token):
        """Privacy Officer can view PIAs."""
        client.cookies.set("access_token", po_token)
        response = client.get("/pias")
        assert response.status_code == 200

    def test_staff_can_view_pias(self, client, staff_token):
        """Staff can view PIAs (read-only)."""
        client.cookies.set("access_token", staff_token)
        response = client.get("/pias")
        assert response.status_code == 200


class TestOrganizationSettingsAccess:
    """Test organization settings access for different roles."""

    def test_admin_can_access_settings(self, client, admin_token):
        """Admin can access organization settings."""
        client.cookies.set("access_token", admin_token)
        response = client.get("/settings")
        assert response.status_code == 200
        assert "Organization Settings" in response.text

    def test_privacy_officer_can_access_settings(self, client, po_token):
        """Privacy Officer can view settings."""
        client.cookies.set("access_token", po_token)
        response = client.get("/settings")
        assert response.status_code == 200

    def test_staff_can_access_settings(self, client, staff_token):
        """Staff can view settings."""
        client.cookies.set("access_token", staff_token)
        response = client.get("/settings")
        assert response.status_code == 200

    def test_admin_can_update_settings(self, client, admin_token):
        """Admin can update organization settings."""
        client.cookies.set("access_token", admin_token)
        response = client.put(
            "/api/settings",
            json={
                "name": "Updated Organization",
                "industry": "Finance"
            }
        )
        assert response.status_code == 200


class TestRequestsAccess:
    """Test access requests functionality for different roles."""

    def test_admin_can_view_requests(self, client, admin_token):
        """Admin can view access requests."""
        client.cookies.set("access_token", admin_token)
        response = client.get("/requests")
        assert response.status_code == 200

    def test_privacy_officer_can_view_requests(self, client, po_token):
        """Privacy Officer can view access requests."""
        client.cookies.set("access_token", po_token)
        response = client.get("/requests")
        assert response.status_code == 200

    def test_staff_can_view_requests(self, client, staff_token):
        """Staff can view access requests."""
        client.cookies.set("access_token", staff_token)
        response = client.get("/requests")
        assert response.status_code == 200


class TestIncidentsAccess:
    """Test breach incidents functionality for different roles."""

    def test_admin_can_view_incidents(self, client, admin_token):
        """Admin can view breach incidents."""
        client.cookies.set("access_token", admin_token)
        response = client.get("/incidents")
        assert response.status_code == 200

    def test_privacy_officer_can_view_incidents(self, client, po_token):
        """Privacy Officer can view breach incidents."""
        client.cookies.set("access_token", po_token)
        response = client.get("/incidents")
        assert response.status_code == 200

    def test_staff_can_view_incidents(self, client, staff_token):
        """Staff can view breach incidents."""
        client.cookies.set("access_token", staff_token)
        response = client.get("/incidents")
        assert response.status_code == 200


class TestRoleEnforcement:
    """Test role enforcement in the system."""

    def test_user_roles_enum_values(self):
        """Test that UserRole enum has correct values."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.PRIVACY_OFFICER.value == "privacy_officer"
        assert UserRole.STAFF.value == "staff"

    def test_admin_role_assigned_correctly(self, admin_user):
        """Admin role is assigned correctly."""
        assert admin_user.role == UserRole.ADMIN.value

    def test_privacy_officer_role_assigned_correctly(self, privacy_officer_user):
        """Privacy Officer role is assigned correctly."""
        assert privacy_officer_user.role == UserRole.PRIVACY_OFFICER.value

    def test_staff_role_assigned_correctly(self, staff_user):
        """Staff role is assigned correctly."""
        assert staff_user.role == UserRole.STAFF.value
