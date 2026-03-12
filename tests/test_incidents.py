"""Tests for Breach Incident Logger functionality."""

import pytest
from fastapi import status
from datetime import datetime, timedelta
from src.app.models import BreachIncident, RiskLevel, BreachIncidentStatus


def test_incidents_unauthenticated(client):
    """Test that unauthenticated users are redirected to login."""
    response = client.get("/incidents")
    assert response.status_code == status.HTTP_200_OK
    assert response.url.path == "/web/login"


def test_incidents_authenticated_empty(client, test_user):
    """Test incidents page shows empty state when no incidents exist."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access incidents page
    response = client.get("/incidents", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"No Incidents Logged" in response.content


def test_incidents_authenticated_with_data(client, db, test_user):
    """Test incidents page displays entries with severity color coding."""
    # Create a test incident
    incident = BreachIncident(
        title="Unauthorized Database Access",
        description="Unauthorized access detected in customer database",
        severity=RiskLevel.HIGH,
        date_discovered=datetime.now(),
        affected_records_count=500,
        data_types_affected={"names": True, "addresses": True, "health_info": False, "financial": False, "government_ids": False, "other": False},
        containment_actions="Database access revoked, passwords reset",
        status=BreachIncidentStatus.INVESTIGATING,
        organization_id=test_user.organization_id
    )
    db.add(incident)
    db.commit()

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access incidents page
    response = client.get("/incidents", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"Unauthorized Database Access" in response.content
    assert b"High" in response.content
    assert b"Investigating" in response.content


def test_create_incident(client, db, test_user):
    """Test POST /api/incidents creates a new incident."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create incident
    date_discovered = datetime.now().strftime("%Y-%m-%d")

    response = client.post(
        "/api/incidents",
        data={
            "title": "Ransomware Attack",
            "description": "Ransomware encrypted multiple servers",
            "severity": "critical",
            "date_discovered": date_discovered,
            "affected_records_count": "1000",
            "data_types_names": "on",
            "data_types_financial": "on",
            "containment_actions": "Servers isolated, backups being restored",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/incidents"

    # Verify incident was created in database
    incident = db.query(BreachIncident).filter(
        BreachIncident.title == "Ransomware Attack"
    ).first()
    assert incident is not None
    assert incident.severity == RiskLevel.CRITICAL
    assert incident.description == "Ransomware encrypted multiple servers"
    assert incident.affected_records_count == 1000
    assert incident.data_types_affected["names"] is True
    assert incident.data_types_affected["financial"] is True
    assert incident.data_types_affected["health_info"] is False
    assert incident.containment_actions == "Servers isolated, backups being restored"
    assert incident.status == BreachIncidentStatus.DETECTED
    assert incident.organization_id == test_user.organization_id


def test_update_incident(client, db, test_user):
    """Test POST /api/incidents/{id} updates an existing incident."""
    # Create a test incident
    incident = BreachIncident(
        title="Original Title",
        description="Original description",
        severity=RiskLevel.LOW,
        date_discovered=datetime.now(),
        affected_records_count=10,
        data_types_affected={"names": True, "addresses": False, "health_info": False, "financial": False, "government_ids": False, "other": False},
        containment_actions="Initial actions",
        status=BreachIncidentStatus.DETECTED,
        organization_id=test_user.organization_id
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    original_id = incident.id

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Update incident
    notification_date = datetime.now().strftime("%Y-%m-%d")
    response = client.post(
        f"/api/incidents/{incident.id}",
        data={
            "title": "Updated Title",
            "description": "Updated description",
            "severity": "high",
            "date_discovered": incident.date_discovered.strftime("%Y-%m-%d"),
            "affected_records_count": "500",
            "data_types_names": "on",
            "data_types_addresses": "on",
            "data_types_health": "on",
            "containment_actions": "Additional containment measures applied",
            "status": "contained",
            "notification_date": notification_date,
            "authority_notified": "WA Privacy Commissioner",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == f"/incidents/{incident.id}"

    # Verify incident was updated
    db.refresh(incident)
    assert incident.id == original_id
    assert incident.title == "Updated Title"
    assert incident.description == "Updated description"
    assert incident.severity == RiskLevel.HIGH
    assert incident.affected_records_count == 500
    assert incident.data_types_affected["names"] is True
    assert incident.data_types_affected["addresses"] is True
    assert incident.data_types_affected["health_info"] is True
    assert incident.containment_actions == "Additional containment measures applied"
    assert incident.status == BreachIncidentStatus.CONTAINED
    assert incident.authority_notified == "WA Privacy Commissioner"
    assert incident.notification_date is not None


def test_update_incident_not_found(client, test_user):
    """Test updating non-existent incident returns 404."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Try to update non-existent incident
    response = client.post(
        "/api/incidents/99999",
        data={
            "title": "Test",
            "severity": "low",
            "date_discovered": "2024-01-01",
            "status": "detected",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_incident_status_transition(client, db, test_user):
    """Test PATCH /api/incidents/{id}/status transitions incident status."""
    # Create a test incident
    incident = BreachIncident(
        title="Test Incident",
        description="Test description",
        severity=RiskLevel.MEDIUM,
        date_discovered=datetime.now(),
        status=BreachIncidentStatus.DETECTED,
        organization_id=test_user.organization_id
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Transition status
    response = client.patch(
        f"/api/incidents/{incident.id}/status",
        data={"status": "investigating"},
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_200_OK

    # Verify status was updated
    db.refresh(incident)
    assert incident.status == BreachIncidentStatus.INVESTIGATING


def test_severity_levels_display(client, db, test_user):
    """Test that severity levels have distinct visual indicators."""
    # Create incidents with different severity levels
    for severity in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]:
        incident = BreachIncident(
            title=f"Incident {severity.value}",
            description=f"Incident with {severity.value} severity",
            severity=severity,
            date_discovered=datetime.now(),
            status=BreachIncidentStatus.DETECTED,
            organization_id=test_user.organization_id
        )
        db.add(incident)
    db.commit()

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access incidents page
    response = client.get("/incidents", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    content = response.content.decode()

    # Check for severity badges with distinct colors
    assert "bg-blue-100 text-blue-800" in content  # Low - blue
    assert "bg-yellow-100 text-yellow-800" in content  # Medium - yellow
    assert "bg-orange-100 text-orange-800" in content  # High - orange
    assert "bg-red-100 text-red-800" in content  # Critical - red


def test_status_levels_display(client, db, test_user):
    """Test that status levels have appropriate visual indicators."""
    # Create incidents with different statuses
    for status_val in [BreachIncidentStatus.DETECTED, BreachIncidentStatus.INVESTIGATING,
                       BreachIncidentStatus.CONTAINED, BreachIncidentStatus.RESOLVED, BreachIncidentStatus.REPORTED]:
        incident = BreachIncident(
            title=f"Incident {status_val.value}",
            description=f"Incident with status {status_val.value}",
            severity=RiskLevel.MEDIUM,
            date_discovered=datetime.now(),
            status=status_val,
            organization_id=test_user.organization_id
        )
        db.add(incident)
    db.commit()

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access incidents page
    response = client.get("/incidents", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    content = response.content.decode()

    # Check for status badges
    assert "Detected" in content
    assert "Investigating" in content
    assert "Contained" in content
    assert "Resolved" in content
    assert "Reported" in content


def test_multi_tenant_isolation(client, db, test_org, test_user):
    """Test that users can only see and modify incidents from their own organization."""
    from src.app.models import Organization, User
    from src.app.auth import get_password_hash

    # Create second organization and user
    org2 = Organization(name="Other Org", abn="98765432101", industry="Finance")
    db.add(org2)
    db.commit()
    db.refresh(org2)

    user2 = User(
        email="other@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Other User",
        role="admin",
        organization_id=org2.id
    )
    db.add(user2)
    db.commit()

    # Create incidents for both organizations
    incident1 = BreachIncident(
        title="Org 1 Incident",
        description="Incident from org 1",
        severity=RiskLevel.HIGH,
        date_discovered=datetime.now(),
        status=BreachIncidentStatus.DETECTED,
        organization_id=test_user.organization_id
    )
    incident2 = BreachIncident(
        title="Org 2 Incident",
        description="Incident from org 2",
        severity=RiskLevel.CRITICAL,
        date_discovered=datetime.now(),
        status=BreachIncidentStatus.INVESTIGATING,
        organization_id=org2.id
    )
    db.add(incident1)
    db.add(incident2)
    db.commit()
    db.refresh(incident1)
    db.refresh(incident2)

    # Login as first user
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Verify first user can see their incident but not the other
    response = client.get("/incidents", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"Org 1 Incident" in response.content
    assert b"Org 2 Incident" not in response.content

    # Verify first user cannot update second org's incident
    response = client.post(
        f"/api/incidents/{incident2.id}",
        data={
            "title": "Hacked",
            "severity": "low",
            "date_discovered": "2024-01-01",
            "status": "resolved",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Verify incident2 was not modified
    db.refresh(incident2)
    assert incident2.title == "Org 2 Incident"


def test_incidents_page_content(client, db, test_user):
    """Test that incidents page contains required information."""
    # Create incidents with different severities and statuses
    incident1 = BreachIncident(
        title="Email Server Breach",
        description="Unauthorized access to email server",
        severity=RiskLevel.CRITICAL,
        date_discovered=datetime.now(),
        affected_records_count=1500,
        status=BreachIncidentStatus.INVESTIGATING,
        organization_id=test_user.organization_id
    )
    incident2 = BreachIncident(
        title="Lost Laptop",
        description="Employee laptop with customer data lost",
        severity=RiskLevel.MEDIUM,
        date_discovered=datetime.now() - timedelta(days=5),
        affected_records_count=50,
        status=BreachIncidentStatus.CONTAINED,
        organization_id=test_user.organization_id
    )
    db.add(incident1)
    db.add(incident2)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )

    # Access page
    response = client.get("/incidents", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK

    # Check for required fields in table
    assert b"Email Server Breach" in response.content
    assert b"Lost Laptop" in response.content
    assert b"Critical" in response.content
    assert b"Medium" in response.content
    assert b"Investigating" in response.content
    assert b"Contained" in response.content
    assert b"1500" in response.content
    assert b"50" in response.content

    # Check for mandatory breach notification info
    assert b"Mandatory Breach Notification" in response.content or b"mandatory notification" in response.content.lower()


def test_incidents_filters(client, db, test_user):
    """Test that incidents page has filters for severity and status."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )

    # Access page
    response = client.get("/incidents", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK

    # Check for filter elements
    content = response.content.decode()
    assert "Filter by Severity" in content
    assert "Filter by Status" in content
    assert "severityFilter" in content
    assert "statusFilter" in content


def test_data_types_affected_checkboxes(client, db, test_user):
    """Test that data types affected are properly stored and displayed."""
    # Create incident with multiple data types
    incident = BreachIncident(
        title="Multi-type Breach",
        description="Breach affecting multiple data types",
        severity=RiskLevel.HIGH,
        date_discovered=datetime.now(),
        affected_records_count=200,
        data_types_affected={
            "names": True,
            "addresses": True,
            "health_info": True,
            "financial": False,
            "government_ids": False,
            "other": True
        },
        status=BreachIncidentStatus.INVESTIGATING,
        organization_id=test_user.organization_id
    )
    db.add(incident)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )

    # Access page
    response = client.get("/incidents", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    content = response.content.decode()

    # The data types should be in the details section
    assert "Names" in content
    assert "Addresses" in content
    assert "Health Info" in content
    assert "Other" in content


def test_notification_details_tracking(client, db, test_user):
    """Test that notification details are properly tracked."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create incident with notification details
    notification_date = datetime.now().strftime("%Y-%m-%d")
    response = client.post(
        "/api/incidents",
        data={
            "title": "Reportable Breach",
            "description": "Serious breach requiring notification",
            "severity": "critical",
            "date_discovered": notification_date,
            "affected_records_count": "5000",
            "data_types_names": "on",
            "data_types_health": "on",
            "containment_actions": "Systems shut down immediately",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Update with notification details
    incident = db.query(BreachIncident).filter(
        BreachIncident.title == "Reportable Breach"
    ).first()

    response = client.post(
        f"/api/incidents/{incident.id}",
        data={
            "title": "Reportable Breach",
            "description": "Serious breach requiring notification",
            "severity": "critical",
            "date_discovered": notification_date,
            "affected_records_count": "5000",
            "data_types_names": "on",
            "data_types_health": "on",
            "containment_actions": "Systems shut down immediately",
            "status": "reported",
            "notification_date": notification_date,
            "authority_notified": "Office of the Australian Information Commissioner (OAIC)",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify notification details were saved
    db.refresh(incident)
    assert incident.notification_date is not None
    assert incident.authority_notified == "Office of the Australian Information Commissioner (OAIC)"
    assert incident.status == BreachIncidentStatus.REPORTED
