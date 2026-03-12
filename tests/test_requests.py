"""Tests for Access and Correction Request tracker functionality."""

import pytest
from fastapi import status
from datetime import date, timedelta
from src.app.models import AccessRequest, RequestType, AccessRequestStatus


def test_requests_unauthenticated(client):
    """Test that unauthenticated users are redirected to login."""
    response = client.get("/requests")
    assert response.status_code == status.HTTP_200_OK
    assert response.url.path == "/web/login"


def test_requests_authenticated_empty(client, test_user):
    """Test requests page shows empty state when no requests exist."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access requests page
    response = client.get("/requests", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"No Requests Logged" in response.content


def test_requests_authenticated_with_data(client, db, test_user):
    """Test requests page displays entries."""
    # Create a test access request
    due_date = date.today() + timedelta(days=45)
    request_obj = AccessRequest(
        requester_name="John Doe",
        requester_email="john.doe@example.com",
        request_type=RequestType.ACCESS,
        description="Request access to my personal information",
        status=AccessRequestStatus.RECEIVED,
        due_date=due_date,
        organization_id=test_user.organization_id
    )
    db.add(request_obj)
    db.commit()

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access requests page
    response = client.get("/requests", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"John Doe" in response.content
    assert b"john.doe@example.com" in response.content
    assert b"Access" in response.content


def test_create_request_with_auto_due_date(client, db, test_user):
    """Test POST /api/requests creates a new request with auto-calculated due date."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create request
    today = date.today()
    expected_due_date = today + timedelta(days=45)

    response = client.post(
        "/api/requests",
        data={
            "requester_name": "Jane Smith",
            "requester_email": "jane.smith@example.com",
            "request_type": "correction",
            "description": "Please correct my address in your records",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/requests"

    # Verify request was created in database with correct due date
    request_obj = db.query(AccessRequest).filter(
        AccessRequest.requester_email == "jane.smith@example.com"
    ).first()
    assert request_obj is not None
    assert request_obj.requester_name == "Jane Smith"
    assert request_obj.request_type == RequestType.CORRECTION
    assert request_obj.description == "Please correct my address in your records"
    assert request_obj.status == AccessRequestStatus.RECEIVED
    assert request_obj.due_date == expected_due_date
    assert request_obj.organization_id == test_user.organization_id


def test_create_request_with_assigned_handler(client, db, test_user):
    """Test POST /api/requests with assigned handler."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create request with assigned handler
    response = client.post(
        "/api/requests",
        data={
            "requester_name": "Bob Johnson",
            "requester_email": "bob@example.com",
            "request_type": "access",
            "description": "Request to view my data",
            "assigned_handler_id": str(test_user.id),
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify request was created with assigned handler
    request_obj = db.query(AccessRequest).filter(
        AccessRequest.requester_email == "bob@example.com"
    ).first()
    assert request_obj is not None
    assert request_obj.assigned_handler_id == test_user.id
    assert request_obj.assigned_handler.full_name == test_user.full_name


def test_update_request(client, db, test_user):
    """Test POST /api/requests/{id} updates an existing request."""
    # Create a test request
    due_date = date.today() + timedelta(days=45)
    request_obj = AccessRequest(
        requester_name="Original Name",
        requester_email="original@example.com",
        request_type=RequestType.ACCESS,
        description="Original description",
        status=AccessRequestStatus.RECEIVED,
        due_date=due_date,
        organization_id=test_user.organization_id
    )
    db.add(request_obj)
    db.commit()
    db.refresh(request_obj)
    original_id = request_obj.id

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Update request
    completion_date = date.today()
    response = client.post(
        f"/api/requests/{request_obj.id}",
        data={
            "requester_name": "Updated Name",
            "requester_email": "updated@example.com",
            "request_type": "correction",
            "description": "Updated description",
            "status": "completed",
            "response_notes": "Request fulfilled",
            "date_completed": completion_date.strftime("%Y-%m-%d"),
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/requests"

    # Verify request was updated
    db.refresh(request_obj)
    assert request_obj.id == original_id
    assert request_obj.requester_name == "Updated Name"
    assert request_obj.requester_email == "updated@example.com"
    assert request_obj.request_type == RequestType.CORRECTION
    assert request_obj.description == "Updated description"
    assert request_obj.status == AccessRequestStatus.COMPLETED
    assert request_obj.response_notes == "Request fulfilled"
    assert request_obj.date_completed == completion_date


def test_update_request_not_found(client, test_user):
    """Test updating non-existent request returns 404."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Try to update non-existent request
    response = client.post(
        "/api/requests/99999",
        data={
            "requester_name": "Test",
            "requester_email": "test@example.com",
            "request_type": "access",
            "status": "received",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_due_date_calculation(client, db, test_user):
    """Test that due date is correctly calculated as 45 days from creation."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create request
    creation_date = date.today()
    expected_due_date = creation_date + timedelta(days=45)

    response = client.post(
        "/api/requests",
        data={
            "requester_name": "Test User",
            "requester_email": "test.due@example.com",
            "request_type": "access",
            "description": "Test due date calculation",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify due date
    request_obj = db.query(AccessRequest).filter(
        AccessRequest.requester_email == "test.due@example.com"
    ).first()
    assert request_obj is not None
    assert request_obj.due_date == expected_due_date


def test_multi_tenant_isolation(client, db, test_org, test_user):
    """Test that users can only see and modify requests from their own organization."""
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

    # Create requests for both organizations
    due_date = date.today() + timedelta(days=45)
    request1 = AccessRequest(
        requester_name="Org 1 Requester",
        requester_email="requester1@example.com",
        request_type=RequestType.ACCESS,
        description="Request from org 1",
        status=AccessRequestStatus.RECEIVED,
        due_date=due_date,
        organization_id=test_user.organization_id
    )
    request2 = AccessRequest(
        requester_name="Org 2 Requester",
        requester_email="requester2@example.com",
        request_type=RequestType.CORRECTION,
        description="Request from org 2",
        status=AccessRequestStatus.RECEIVED,
        due_date=due_date,
        organization_id=org2.id
    )
    db.add(request1)
    db.add(request2)
    db.commit()
    db.refresh(request1)
    db.refresh(request2)

    # Login as first user
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Verify first user can see their request but not the other
    response = client.get("/requests", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"Org 1 Requester" in response.content
    assert b"Org 2 Requester" not in response.content

    # Verify first user cannot update second org's request
    response = client.post(
        f"/api/requests/{request2.id}",
        data={
            "requester_name": "Hacked",
            "requester_email": "hacked@example.com",
            "request_type": "access",
            "status": "denied",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Verify request2 was not modified
    db.refresh(request2)
    assert request2.requester_name == "Org 2 Requester"


def test_requests_page_content(client, db, test_user):
    """Test that requests page contains required information."""
    # Create requests with different types and statuses
    due_date1 = date.today() + timedelta(days=45)
    due_date2 = date.today() + timedelta(days=10)

    request1 = AccessRequest(
        requester_name="Alice Brown",
        requester_email="alice@example.com",
        request_type=RequestType.ACCESS,
        description="Need to see my information",
        status=AccessRequestStatus.RECEIVED,
        due_date=due_date1,
        assigned_handler_id=test_user.id,
        organization_id=test_user.organization_id
    )
    request2 = AccessRequest(
        requester_name="Charlie Davis",
        requester_email="charlie@example.com",
        request_type=RequestType.CORRECTION,
        description="Incorrect phone number",
        status=AccessRequestStatus.IN_PROGRESS,
        due_date=due_date2,
        organization_id=test_user.organization_id
    )
    db.add(request1)
    db.add(request2)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )

    # Access page
    response = client.get("/requests", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK

    # Check for required fields in table
    assert b"Alice Brown" in response.content
    assert b"alice@example.com" in response.content
    assert b"Charlie Davis" in response.content
    assert b"charlie@example.com" in response.content
    assert b"Access" in response.content
    assert b"Correction" in response.content
    assert b"Received" in response.content
    assert b"In Progress" in response.content

    # Check for IPP reference
    assert b"IPPs 6 & 7" in response.content or b"IPP" in response.content


def test_requests_filters(client, db, test_user):
    """Test that requests page has filters for status and type."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )

    # Access page
    response = client.get("/requests", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK

    # Check for filter elements
    content = response.content.decode()
    assert "Filter by Status" in content
    assert "Filter by Type" in content
    assert "statusFilter" in content
    assert "typeFilter" in content


def test_request_status_badges(client, db, test_user):
    """Test that requests display proper status badges."""
    # Create requests with different statuses
    due_date = date.today() + timedelta(days=45)

    for status_val in [AccessRequestStatus.RECEIVED, AccessRequestStatus.IN_PROGRESS,
                       AccessRequestStatus.COMPLETED, AccessRequestStatus.DENIED]:
        request_obj = AccessRequest(
            requester_name=f"User {status_val.value}",
            requester_email=f"{status_val.value}@example.com",
            request_type=RequestType.ACCESS,
            description=f"Request with status {status_val.value}",
            status=status_val,
            due_date=due_date,
            organization_id=test_user.organization_id
        )
        db.add(request_obj)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access page
    response = client.get("/requests", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    content = response.content.decode()

    # Check for status badges with appropriate styling
    assert "Received" in content
    assert "In Progress" in content
    assert "Completed" in content
    assert "Denied" in content
