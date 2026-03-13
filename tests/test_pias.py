"""Tests for PIA (Privacy Impact Assessment) functionality."""

import pytest
from fastapi import status
from src.app.models import PIA, PIAStatus, RiskLevel


def test_pias_list_unauthenticated(client):
    """Test that unauthenticated users are redirected to login."""
    response = client.get("/pias")
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)
    assert response.url.path == "/web/login"


def test_pias_list_authenticated_empty(client, test_user):
    """Test PIAs list page shows empty state when no PIAs exist."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Access PIAs page
    response = client.get("/pias", follow_redirects=False)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)
    assert b"No PIAs" in response.content


def test_pias_list_authenticated_with_data(client, db, test_user):
    """Test PIAs list page displays PIAs."""
    # Create a test PIA
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

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Access PIAs page
    response = client.get("/pias", follow_redirects=False)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)
    assert b"Test PIA" in response.content
    assert b"Medium" in response.content
    assert b"Draft" in response.content


def test_pias_new_page(client, test_user):
    """Test PIA creation form page loads."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Access new PIA page
    response = client.get("/pias/new", follow_redirects=False)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)
    assert b"Create New Privacy Impact Assessment" in response.content
    assert b"PIA Title" in response.content
    assert b"Data Types Involved" in response.content


def test_create_pia(client, db, test_user):
    """Test POST /api/pias creates a new PIA in draft status."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

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
            "risk_level": "high",
            "mitigation_measures": "Implement encryption, access controls, and audit logging"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/pias"

    # Verify PIA was created in database
    pia = db.query(PIA).filter(PIA.title == "Customer Portal Upgrade").first()
    assert pia is not None
    assert pia.description == "Upgrading our customer portal with new features"
    assert pia.status == PIAStatus.DRAFT
    assert pia.risk_level == RiskLevel.HIGH
    assert pia.data_types["names"] is True
    assert pia.data_types["addresses"] is True
    assert pia.data_types["financial"] is True
    assert pia.data_types["health_info"] is False
    assert pia.data_flow_description == "Data collected via web forms, stored in database"
    assert pia.mitigation_measures == "Implement encryption, access controls, and audit logging"
    assert pia.organization_id == test_user.organization_id
    assert pia.created_by == test_user.id


def test_pias_detail_page(client, db, test_user):
    """Test PIA detail page displays full PIA information."""
    # Create a test PIA
    pia = PIA(
        title="Test PIA Detail",
        description="Test description for detail view",
        data_types={"names": True, "health_info": True},
        data_flow_description="Data flows securely",
        risk_level=RiskLevel.CRITICAL,
        mitigation_measures="Enhanced security measures",
        status=PIAStatus.IN_REVIEW,
        organization_id=test_user.organization_id,
        created_by=test_user.id
    )
    db.add(pia)
    db.commit()
    db.refresh(pia)

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Access PIA detail page
    response = client.get(f"/pias/{pia.id}", follow_redirects=False)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)
    assert b"Test PIA Detail" in response.content
    assert b"Test description for detail view" in response.content
    assert b"Critical" in response.content
    assert b"In Review" in response.content
    assert b"Data flows securely" in response.content
    assert b"Enhanced security measures" in response.content


def test_pias_detail_not_found(client, test_user):
    """Test PIA detail page returns 404 for non-existent PIA."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Try to access non-existent PIA
    response = client.get("/pias/99999", follow_redirects=False)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_pia(client, db, test_user):
    """Test PUT /api/pias/{id} updates PIA fields."""
    # Create a test PIA
    pia = PIA(
        title="Original Title",
        description="Original description",
        data_types={"names": True},
        data_flow_description="Original flow",
        risk_level=RiskLevel.LOW,
        mitigation_measures="Original measures",
        status=PIAStatus.DRAFT,
        organization_id=test_user.organization_id,
        created_by=test_user.id
    )
    db.add(pia)
    db.commit()
    db.refresh(pia)
    original_id = pia.id

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Update PIA (using POST since HTML forms only support POST)
    response = client.post(
        f"/api/pias/{pia.id}",
        data={
            "title": "Updated Title",
            "description": "Updated description",
            "data_types_names": "false",
            "data_types_addresses": "true",
            "data_types_health": "true",
            "data_types_financial": "false",
            "data_types_gov_ids": "false",
            "data_types_other": "true",
            "data_flow_description": "Updated flow description",
            "risk_level": "critical",
            "mitigation_measures": "Updated mitigation measures"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == f"/pias/{pia.id}"

    # Verify PIA was updated in database
    db.refresh(pia)
    assert pia.id == original_id
    assert pia.title == "Updated Title"
    assert pia.description == "Updated description"
    assert pia.risk_level == RiskLevel.CRITICAL
    assert pia.data_types["names"] is False
    assert pia.data_types["addresses"] is True
    assert pia.data_types["health_info"] is True
    assert pia.data_types["other"] is True
    assert pia.data_flow_description == "Updated flow description"
    assert pia.mitigation_measures == "Updated mitigation measures"


def test_update_pia_not_found(client, test_user):
    """Test updating non-existent PIA returns 404."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Try to update non-existent PIA
    response = client.post(
        "/api/pias/99999",
        data={
            "title": "Test",
            "description": "Test",
            "data_flow_description": "Test",
            "risk_level": "low",
            "mitigation_measures": "Test"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_pia_status_draft_to_in_review(client, db, test_user):
    """Test PATCH /api/pias/{id}/status transitions status from draft to in_review."""
    # Create a test PIA
    pia = PIA(
        title="Status Test PIA",
        description="Testing status transitions",
        data_types={"names": True},
        data_flow_description="Test flow",
        risk_level=RiskLevel.MEDIUM,
        mitigation_measures="Test measures",
        status=PIAStatus.DRAFT,
        organization_id=test_user.organization_id,
        created_by=test_user.id
    )
    db.add(pia)
    db.commit()
    db.refresh(pia)

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Update status to in_review
    response = client.post(
        f"/api/pias/{pia.id}/status",
        data={"status": "in_review"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)


    # Verify status was updated in database
    db.refresh(pia)
    assert pia.status == PIAStatus.IN_REVIEW


def test_update_pia_status_in_review_to_approved(client, db, test_user):
    """Test PATCH /api/pias/{id}/status transitions status from in_review to approved."""
    # Create a test PIA in review
    pia = PIA(
        title="Approval Test PIA",
        description="Testing approval",
        data_types={"names": True},
        data_flow_description="Test flow",
        risk_level=RiskLevel.LOW,
        mitigation_measures="Test measures",
        status=PIAStatus.IN_REVIEW,
        organization_id=test_user.organization_id,
        created_by=test_user.id
    )
    db.add(pia)
    db.commit()
    db.refresh(pia)

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Approve the PIA
    response = client.post(
        f"/api/pias/{pia.id}/status",
        data={"status": "approved"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)


    # Verify status was updated in database
    db.refresh(pia)
    assert pia.status == PIAStatus.APPROVED


def test_update_pia_status_in_review_to_rejected(client, db, test_user):
    """Test PATCH /api/pias/{id}/status transitions status from in_review to rejected."""
    # Create a test PIA in review
    pia = PIA(
        title="Rejection Test PIA",
        description="Testing rejection",
        data_types={"names": True},
        data_flow_description="Test flow",
        risk_level=RiskLevel.HIGH,
        mitigation_measures="Insufficient measures",
        status=PIAStatus.IN_REVIEW,
        organization_id=test_user.organization_id,
        created_by=test_user.id
    )
    db.add(pia)
    db.commit()
    db.refresh(pia)

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Reject the PIA
    response = client.post(
        f"/api/pias/{pia.id}/status",
        data={"status": "rejected"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)


    # Verify status was updated in database
    db.refresh(pia)
    assert pia.status == PIAStatus.REJECTED


def test_update_pia_status_unauthenticated(client, db, test_user):
    """Test status update fails when not authenticated."""
    # Create a test PIA
    pia = PIA(
        title="Auth Test PIA",
        description="Testing authentication",
        data_types={"names": True},
        data_flow_description="Test flow",
        risk_level=RiskLevel.MEDIUM,
        mitigation_measures="Test measures",
        status=PIAStatus.DRAFT,
        organization_id=test_user.organization_id,
        created_by=test_user.id
    )
    db.add(pia)
    db.commit()
    db.refresh(pia)

    # Try to update status without authentication
    response = client.post(
        f"/api/pias/{pia.id}/status",
        data={"status": "in_review"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_multi_tenant_isolation(client, db, test_org, test_user):
    """Test that users can only see PIAs from their own organization."""
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

    # Create PIAs for both organizations
    pia1 = PIA(
        title="Org 1 PIA",
        description="PIA for first org",
        data_types={"names": True},
        data_flow_description="Test flow",
        risk_level=RiskLevel.LOW,
        mitigation_measures="Test measures",
        status=PIAStatus.DRAFT,
        organization_id=test_user.organization_id,
        created_by=test_user.id
    )
    pia2 = PIA(
        title="Org 2 PIA",
        description="PIA for second org",
        data_types={"names": True},
        data_flow_description="Test flow",
        risk_level=RiskLevel.HIGH,
        mitigation_measures="Test measures",
        status=PIAStatus.DRAFT,
        organization_id=org2.id,
        created_by=user2.id
    )
    db.add(pia1)
    db.add(pia2)
    db.commit()
    db.refresh(pia1)
    db.refresh(pia2)

    # Login as first user
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)

    # Verify first user can see their PIA
    response = client.get("/pias", follow_redirects=False)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_303_SEE_OTHER, status.HTTP_302_FOUND)
    assert b"Org 1 PIA" in response.content
    assert b"Org 2 PIA" not in response.content

    # Verify first user cannot access second org's PIA
    response = client.get(f"/pias/{pia2.id}", follow_redirects=False)
    assert response.status_code == status.HTTP_404_NOT_FOUND
