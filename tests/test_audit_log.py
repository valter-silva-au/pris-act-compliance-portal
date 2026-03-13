"""Tests for Audit Log functionality."""

import pytest
from fastapi import status
from src.app.models import PIA, PIAStatus, RiskLevel, BreachIncident, BreachIncidentStatus, AccessRequest, AccessRequestStatus, RequestType, AuditLog, PrivacyOfficer
from datetime import date, timedelta


def test_audit_log_page_unauthenticated(client):
    """Test that unauthenticated users are redirected to login."""
    response = client.get("/audit-log")
    assert response.status_code == status.HTTP_200_OK
    assert response.url.path == "/web/login"


def test_audit_log_page_authenticated_empty(client, test_user):
    """Test audit log page shows empty state when no logs exist."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access audit log page
    response = client.get("/audit-log", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"No Audit Logs" in response.content


def test_create_pia_generates_audit_log(client, db, test_user):
    """Test that creating a PIA generates an audit log entry."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create PIA
    response = client.post(
        "/api/pias",
        data={
            "title": "Customer Portal Upgrade",
            "description": "Upgrading our customer portal with new features",
            "data_types_names": "true",
            "data_types_addresses": "true",
            "data_types_health": "false",
            "data_types_financial": "true",
            "data_types_gov_ids": "false",
            "data_types_other": "false",
            "data_flow_description": "Data collected via web forms, stored in database",
            "risk_level": "medium",
            "mitigation_measures": "Implement encryption and access controls"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify audit log entry was created
    audit_log = db.query(AuditLog).filter(
        AuditLog.user_id == test_user.id,
        AuditLog.action == "create_pia"
    ).first()

    assert audit_log is not None
    assert audit_log.entity_type == "PIA"
    assert audit_log.entity_id is not None
    assert audit_log.details["title"] == "Customer Portal Upgrade"
    assert audit_log.details["risk_level"] == "medium"
    assert audit_log.details["status"] == "draft"


def test_update_pia_generates_audit_log(client, db, test_user):
    """Test that updating a PIA generates an audit log entry."""
    # Create a test PIA first
    pia = PIA(
        title="Test PIA",
        description="Test description",
        data_types={"names": True, "addresses": False},
        data_flow_description="Data flows through the system",
        risk_level=RiskLevel.MEDIUM,
        mitigation_measures="Implement encryption",
        status=PIAStatus.DRAFT,
        organization_id=test_user.organization_id,
        created_by=test_user.id
    )
    db.add(pia)
    db.commit()
    db.refresh(pia)

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Update PIA
    response = client.post(
        f"/api/pias/{pia.id}",
        data={
            "title": "Updated Test PIA",
            "description": "Updated description",
            "data_types_names": "true",
            "data_types_addresses": "true",
            "data_types_health": "false",
            "data_types_financial": "false",
            "data_types_gov_ids": "false",
            "data_types_other": "false",
            "data_flow_description": "Updated data flow",
            "risk_level": "high",
            "mitigation_measures": "Enhanced security measures"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify audit log entry was created
    audit_log = db.query(AuditLog).filter(
        AuditLog.user_id == test_user.id,
        AuditLog.action == "update_pia"
    ).first()

    assert audit_log is not None
    assert audit_log.entity_type == "PIA"
    assert audit_log.entity_id == pia.id
    assert audit_log.details["title"] == "Updated Test PIA"
    assert audit_log.details["risk_level"] == "high"


def test_create_incident_generates_audit_log(client, db, test_user):
    """Test that creating an incident generates an audit log entry."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create incident
    response = client.post(
        "/api/incidents",
        data={
            "title": "Data Breach",
            "description": "Unauthorized access detected",
            "severity": "high",
            "date_discovered": "2024-01-15",
            "affected_records_count": 100,
            "data_types_names": "true",
            "data_types_addresses": "false",
            "data_types_health": "false",
            "data_types_financial": "true",
            "data_types_gov_ids": "false",
            "data_types_other": "false",
            "containment_actions": "Disabled affected accounts"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify audit log entry was created
    audit_log = db.query(AuditLog).filter(
        AuditLog.user_id == test_user.id,
        AuditLog.action == "create_incident"
    ).first()

    assert audit_log is not None
    assert audit_log.entity_type == "BreachIncident"
    assert audit_log.entity_id is not None
    assert audit_log.details["title"] == "Data Breach"
    assert audit_log.details["severity"] == "high"


def test_update_incident_generates_audit_log(client, db, test_user):
    """Test that updating an incident generates an audit log entry."""
    # Create a test incident first
    from datetime import datetime
    incident = BreachIncident(
        title="Test Incident",
        description="Test description",
        severity=RiskLevel.MEDIUM,
        date_discovered=datetime.now(),
        affected_records_count=50,
        data_types_affected={"names": True},
        status=BreachIncidentStatus.DETECTED,
        organization_id=test_user.organization_id
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Update incident
    response = client.post(
        f"/api/incidents/{incident.id}",
        data={
            "title": "Updated Incident",
            "description": "Updated description",
            "severity": "high",
            "date_discovered": "2024-01-15",
            "affected_records_count": 75,
            "data_types_names": "true",
            "data_types_addresses": "false",
            "data_types_health": "false",
            "data_types_financial": "false",
            "data_types_gov_ids": "false",
            "data_types_other": "false",
            "containment_actions": "Updated actions",
            "status": "investigating"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify audit log entry was created
    audit_log = db.query(AuditLog).filter(
        AuditLog.user_id == test_user.id,
        AuditLog.action == "update_incident"
    ).first()

    assert audit_log is not None
    assert audit_log.entity_type == "BreachIncident"
    assert audit_log.entity_id == incident.id


def test_create_access_request_generates_audit_log(client, db, test_user):
    """Test that creating an access request generates an audit log entry."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create access request
    response = client.post(
        "/api/requests",
        data={
            "requester_name": "John Doe",
            "requester_email": "john@example.com",
            "request_type": "access",
            "description": "Request for personal data"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify audit log entry was created
    audit_log = db.query(AuditLog).filter(
        AuditLog.user_id == test_user.id,
        AuditLog.action == "create_access_request"
    ).first()

    assert audit_log is not None
    assert audit_log.entity_type == "AccessRequest"
    assert audit_log.entity_id is not None
    assert audit_log.details["requester_name"] == "John Doe"
    assert audit_log.details["request_type"] == "access"


def test_update_access_request_generates_audit_log(client, db, test_user):
    """Test that updating an access request generates an audit log entry."""
    # Create a test access request first
    access_request = AccessRequest(
        requester_name="Jane Doe",
        requester_email="jane@example.com",
        request_type=RequestType.ACCESS,
        description="Test request",
        status=AccessRequestStatus.RECEIVED,
        due_date=date.today() + timedelta(days=45),
        organization_id=test_user.organization_id
    )
    db.add(access_request)
    db.commit()
    db.refresh(access_request)

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Update access request
    response = client.post(
        f"/api/requests/{access_request.id}",
        data={
            "requester_name": "Jane Doe Updated",
            "requester_email": "jane@example.com",
            "request_type": "access",
            "description": "Updated request",
            "status": "in_progress",
            "response_notes": "Processing the request"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify audit log entry was created
    audit_log = db.query(AuditLog).filter(
        AuditLog.user_id == test_user.id,
        AuditLog.action == "update_access_request"
    ).first()

    assert audit_log is not None
    assert audit_log.entity_type == "AccessRequest"
    assert audit_log.entity_id == access_request.id


def test_designate_privacy_officer_generates_audit_log(client, db, test_user, test_org):
    """Test that designating a privacy officer generates an audit log entry."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Designate privacy officer
    response = client.post(
        "/api/privacy-officer",
        data={
            "user_id": test_user.id,
            "contact_phone": "0412345678"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify audit log entry was created
    audit_log = db.query(AuditLog).filter(
        AuditLog.user_id == test_user.id,
        AuditLog.action == "designate_privacy_officer"
    ).first()

    assert audit_log is not None
    assert audit_log.entity_type == "PrivacyOfficer"
    assert audit_log.entity_id is not None
    assert audit_log.details["designated_user_id"] == test_user.id


def test_audit_log_page_displays_entries(client, db, test_user):
    """Test that audit log page displays entries correctly."""
    # Create some audit log entries
    audit_log1 = AuditLog(
        user_id=test_user.id,
        action="create_pia",
        entity_type="PIA",
        entity_id=1,
        details={"title": "Test PIA"}
    )
    audit_log2 = AuditLog(
        user_id=test_user.id,
        action="create_incident",
        entity_type="BreachIncident",
        entity_id=2,
        details={"title": "Test Incident"}
    )
    db.add(audit_log1)
    db.add(audit_log2)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access audit log page
    response = client.get("/audit-log", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"Create Pia" in response.content
    assert b"Create Incident" in response.content
    assert b"Test User" in response.content


def test_audit_log_filtering_by_entity_type(client, db, test_user):
    """Test that audit log can be filtered by entity type."""
    # Create audit log entries with different entity types
    audit_log1 = AuditLog(
        user_id=test_user.id,
        action="create_pia",
        entity_type="PIA",
        entity_id=1,
        details={"title": "Test PIA"}
    )
    audit_log2 = AuditLog(
        user_id=test_user.id,
        action="create_incident",
        entity_type="BreachIncident",
        entity_id=2,
        details={"title": "Test Incident"}
    )
    db.add(audit_log1)
    db.add(audit_log2)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access audit log page with entity type filter
    response = client.get("/audit-log?entity_type=PIA", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"Create Pia" in response.content
    # Should not show incident
    assert b"Create Incident" not in response.content


def test_audit_log_filtering_by_date_range(client, db, test_user):
    """Test that audit log can be filtered by date range."""
    from datetime import datetime, timezone

    # Create audit log entries with specific dates
    old_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    recent_date = datetime(2024, 3, 1, tzinfo=timezone.utc)

    audit_log1 = AuditLog(
        user_id=test_user.id,
        action="create_pia",
        entity_type="PIA",
        entity_id=1,
        details={"title": "Old PIA"},
        timestamp=old_date
    )
    audit_log2 = AuditLog(
        user_id=test_user.id,
        action="create_incident",
        entity_type="BreachIncident",
        entity_id=2,
        details={"title": "Recent Incident"},
        timestamp=recent_date
    )
    db.add(audit_log1)
    db.add(audit_log2)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access audit log page with date filter (only recent)
    response = client.get("/audit-log?date_from=2024-02-01", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"Recent Incident" in response.content
    # Should not show old entry
    assert b"Old PIA" not in response.content
