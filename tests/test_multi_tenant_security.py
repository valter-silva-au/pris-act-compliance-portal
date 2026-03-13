"""Security tests for multi-tenant data isolation."""

import pytest
from datetime import date, datetime, timedelta, timezone
from src.app.models import (
    Organization, User, PIA, PIAStatus, RiskLevel, DataRegister,
    AccessRequest, RequestType, AccessRequestStatus, BreachIncident, BreachIncidentStatus
)
from src.app.auth import get_password_hash, create_access_token


@pytest.fixture
def org1(db):
    """Create first organization."""
    org = Organization(
        name="Organization One",
        abn="11111111111",
        industry="Healthcare"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def org2(db):
    """Create second organization."""
    org = Organization(
        name="Organization Two",
        abn="22222222222",
        industry="Finance"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def user_org1(db, org1):
    """Create user in organization 1."""
    user = User(
        email="user1@org1.com",
        hashed_password=get_password_hash("password123"),
        full_name="User One",
        role="admin",
        organization_id=org1.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_org2(db, org2):
    """Create user in organization 2."""
    user = User(
        email="user2@org2.com",
        hashed_password=get_password_hash("password123"),
        full_name="User Two",
        role="admin",
        organization_id=org2.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token_org1(user_org1):
    """Create authentication token for org1 user."""
    return create_access_token(data={"sub": user_org1.email})


@pytest.fixture
def auth_token_org2(user_org2):
    """Create authentication token for org2 user."""
    return create_access_token(data={"sub": user_org2.email})


@pytest.fixture
def pia_org1(db, org1, user_org1):
    """Create PIA for organization 1."""
    pia = PIA(
        title="Org1 PIA - Patient Data System",
        description="Healthcare patient data management",
        data_types={"names": True, "health_info": True},
        data_flow_description="Patient data flows through EHR system",
        risk_level=RiskLevel.HIGH,
        mitigation_measures="Encryption and access controls",
        status=PIAStatus.DRAFT,
        organization_id=org1.id,
        created_by=user_org1.id
    )
    db.add(pia)
    db.commit()
    db.refresh(pia)
    return pia


@pytest.fixture
def pia_org2(db, org2, user_org2):
    """Create PIA for organization 2."""
    pia = PIA(
        title="Org2 PIA - Financial Transactions",
        description="Financial transaction processing",
        data_types={"names": True, "financial": True},
        data_flow_description="Payment data flows",
        risk_level=RiskLevel.CRITICAL,
        mitigation_measures="PCI-DSS compliance",
        status=PIAStatus.IN_REVIEW,
        organization_id=org2.id,
        created_by=user_org2.id
    )
    db.add(pia)
    db.commit()
    db.refresh(pia)
    return pia


@pytest.fixture
def data_register_org1(db, org1):
    """Create data register entry for organization 1."""
    entry = DataRegister(
        data_category="Patient Records",
        description="Medical records of patients",
        storage_location="AWS S3 - Healthcare region",
        access_controls="Role-based access",
        retention_period="7 years",
        legal_basis="Healthcare Act",
        date_last_reviewed=date.today(),
        organization_id=org1.id
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@pytest.fixture
def data_register_org2(db, org2):
    """Create data register entry for organization 2."""
    entry = DataRegister(
        data_category="Transaction Logs",
        description="Financial transaction records",
        storage_location="On-premise datacenter",
        access_controls="Multi-factor auth",
        retention_period="10 years",
        legal_basis="Banking regulations",
        date_last_reviewed=date.today(),
        organization_id=org2.id
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@pytest.fixture
def access_request_org1(db, org1):
    """Create access request for organization 1."""
    request = AccessRequest(
        requester_name="John Patient",
        requester_email="john@example.com",
        request_type=RequestType.ACCESS,
        description="Request for medical records",
        status=AccessRequestStatus.RECEIVED,
        due_date=date.today() + timedelta(days=30),
        organization_id=org1.id
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@pytest.fixture
def access_request_org2(db, org2):
    """Create access request for organization 2."""
    request = AccessRequest(
        requester_name="Jane Customer",
        requester_email="jane@example.com",
        request_type=RequestType.CORRECTION,
        description="Correction of account details",
        status=AccessRequestStatus.IN_PROGRESS,
        due_date=date.today() + timedelta(days=20),
        organization_id=org2.id
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@pytest.fixture
def incident_org1(db, org1):
    """Create breach incident for organization 1."""
    incident = BreachIncident(
        title="Org1 Incident - Unauthorized Access",
        description="Unauthorized access to patient data",
        severity=RiskLevel.HIGH,
        date_discovered=datetime.now(timezone.utc),
        affected_records_count=100,
        data_types_affected={"names": True, "health_info": True},
        containment_actions="Disabled compromised accounts",
        status=BreachIncidentStatus.INVESTIGATING,
        organization_id=org1.id
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@pytest.fixture
def incident_org2(db, org2):
    """Create breach incident for organization 2."""
    incident = BreachIncident(
        title="Org2 Incident - Data Leak",
        description="Financial data exposed",
        severity=RiskLevel.CRITICAL,
        date_discovered=datetime.now(timezone.utc),
        affected_records_count=500,
        data_types_affected={"names": True, "financial": True},
        containment_actions="Secured database",
        status=BreachIncidentStatus.CONTAINED,
        organization_id=org2.id
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


class TestCrossTenantPIAIsolation:
    """Test that PIAs are properly isolated between organizations."""

    def test_pia_list_shows_only_own_org(self, client, user_org1, pia_org1, pia_org2, auth_token_org1):
        """User from Org1 should only see Org1's PIAs."""
        # Set authentication cookie
        client.cookies.set("access_token", auth_token_org1)

        response = client.get("/pias")
        assert response.status_code == 200

        # Should contain Org1 PIA
        assert "Org1 PIA - Patient Data System" in response.text
        # Should NOT contain Org2 PIA
        assert "Org2 PIA - Financial Transactions" not in response.text

    def test_pia_detail_access_denied_for_other_org(self, client, user_org1, pia_org2, auth_token_org1):
        """User from Org1 should not be able to access Org2's PIA details."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.get(f"/pias/{pia_org2.id}")
        # Should get 404 not 200
        assert response.status_code == 404

    def test_pia_update_denied_for_other_org(self, client, user_org1, pia_org2, auth_token_org1):
        """User from Org1 should not be able to update Org2's PIA."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.post(
            f"/api/pias/{pia_org2.id}",
            data={
                "title": "Hacked PIA Title",
                "description": "Unauthorized modification",
                "data_flow_description": "Bad flow",
                "risk_level": "low",
                "mitigation_measures": "None",
                "status": "approved"
            }
        )
        # Should get 404 not redirect
        assert response.status_code == 404


class TestCrossTenantDataRegisterIsolation:
    """Test that data register entries are properly isolated between organizations."""

    def test_data_register_list_shows_only_own_org(self, client, data_register_org1, data_register_org2, auth_token_org1):
        """User from Org1 should only see Org1's data register entries."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.get("/data-register")
        assert response.status_code == 200

        # Should contain Org1 data
        assert "Patient Records" in response.text
        # Should NOT contain Org2 data
        assert "Transaction Logs" not in response.text

    def test_data_register_update_denied_for_other_org(self, client, data_register_org2, auth_token_org1):
        """User from Org1 should not be able to update Org2's data register entry."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.post(
            f"/api/data-register/{data_register_org2.id}",
            data={
                "data_category": "Hacked Category",
                "description": "Unauthorized modification"
            }
        )
        # Should get 404
        assert response.status_code == 404

    def test_data_register_delete_denied_for_other_org(self, client, data_register_org2, auth_token_org1):
        """User from Org1 should not be able to delete Org2's data register entry."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.delete(f"/api/data-register/{data_register_org2.id}")
        # Should get 404
        assert response.status_code == 404


class TestCrossTenantAccessRequestIsolation:
    """Test that access requests are properly isolated between organizations."""

    def test_access_request_list_shows_only_own_org(self, client, access_request_org1, access_request_org2, auth_token_org1):
        """User from Org1 should only see Org1's access requests."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.get("/requests")
        assert response.status_code == 200

        # Should contain Org1 request
        assert "John Patient" in response.text
        # Should NOT contain Org2 request
        assert "Jane Customer" not in response.text

    def test_access_request_update_denied_for_other_org(self, client, access_request_org2, auth_token_org1):
        """User from Org1 should not be able to update Org2's access request."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.post(
            f"/api/requests/{access_request_org2.id}",
            data={
                "requester_name": "John Patient",
                "requester_email": "john@example.com",
                "request_type": "access",
                "description": "Test",
                "status": "completed",
                "due_date": "2024-12-31",
                "response_notes": "Unauthorized access"
            }
        )
        # Should get 404
        assert response.status_code == 404


class TestCrossTenantIncidentIsolation:
    """Test that breach incidents are properly isolated between organizations."""

    def test_incident_list_shows_only_own_org(self, client, incident_org1, incident_org2, auth_token_org1):
        """User from Org1 should only see Org1's incidents."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.get("/incidents")
        assert response.status_code == 200

        # Should contain Org1 incident
        assert "Org1 Incident - Unauthorized Access" in response.text
        # Should NOT contain Org2 incident
        assert "Org2 Incident - Data Leak" not in response.text

    def test_incident_detail_access_denied_for_other_org(self, client, incident_org2, auth_token_org1):
        """User from Org1 should not be able to access Org2's incident details."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.get(f"/incidents/{incident_org2.id}")
        # Should get 404
        assert response.status_code == 404

    def test_incident_update_denied_for_other_org(self, client, incident_org2, user_org2, auth_token_org1, db):
        """User from Org1 should not be able to update Org2's incident."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.post(
            f"/api/incidents/{incident_org2.id}",
            data={
                "title": "Hacked Incident",
                "description": "Unauthorized modification",
                "severity": "low",
                "status": "resolved",
                "date_discovered": "2024-01-01",
                "affected_records_count": "10",
                "data_types_names": "on",
                "containment_actions": "None"
            }
        )
        # Should get 404
        assert response.status_code == 404


class TestDashboardMultiTenantIsolation:
    """Test that dashboard only shows current organization's data."""

    def test_dashboard_shows_only_own_org_data(
        self, client, user_org1,
        pia_org1, pia_org2,
        incident_org1, incident_org2,
        access_request_org1, access_request_org2,
        auth_token_org1
    ):
        """Dashboard should only display data from user's organization."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.get("/dashboard")
        assert response.status_code == 200

        # Verify the dashboard renders successfully
        assert "Dashboard" in response.text

        # Should NOT see Org2 specific data
        assert "Org2 PIA - Financial Transactions" not in response.text
        assert "Org2 Incident - Data Leak" not in response.text
        assert "Jane Customer" not in response.text  # Org2 access request requester


class TestOrganizationSettings:
    """Test organization settings endpoint security."""

    def test_settings_page_shows_own_org_only(self, client, org1, user_org1, auth_token_org1):
        """Settings page should show only current user's organization."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.get("/settings")
        assert response.status_code == 200

        # Should show Org1 info
        assert org1.name in response.text
        assert org1.abn in response.text

    def test_settings_update_only_own_org(self, client, org1, org2, user_org1, auth_token_org1, db):
        """User should only be able to update their own organization."""
        client.cookies.set("access_token", auth_token_org1)

        response = client.put(
            "/api/settings",
            json={
                "name": "Updated Organization One",
                "industry": "Updated Healthcare"
            }
        )
        assert response.status_code == 200

        # Verify Org1 was updated
        db.refresh(org1)
        assert org1.name == "Updated Organization One"
        assert org1.industry == "Updated Healthcare"

        # Verify Org2 was NOT affected
        db.refresh(org2)
        assert org2.name == "Organization Two"
        assert org2.industry == "Finance"

    def test_cannot_view_other_org_settings(self, client, org2, user_org1, auth_token_org1):
        """User cannot view another organization's settings."""
        client.cookies.set("access_token", auth_token_org1)

        # Try to access settings - should only see own org
        response = client.get("/settings")
        assert response.status_code == 200

        # Should NOT contain Org2 details
        assert org2.name not in response.text
        assert org2.abn not in response.text
