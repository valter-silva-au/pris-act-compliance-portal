"""Tests for notification and reminder system functionality."""

import pytest
from fastapi import status
from datetime import date, datetime, timedelta, timezone
from src.app.models import (
    Notification, AccessRequest, AccessRequestStatus, RequestType,
    PIA, PIAStatus, RiskLevel, IPPAssessment, ComplianceStatus,
    BreachIncident, BreachIncidentStatus
)
from src.app.notifications import (
    create_notification,
    get_unread_notifications,
    mark_notification_as_read,
    get_unread_count,
    check_and_create_request_reminders,
    check_and_create_pia_reminders,
    check_and_create_ipp_reminders,
    check_and_create_breach_reminders,
    check_and_create_all_reminders
)


def test_create_notification(db, test_user):
    """Test creating a notification."""
    notification = create_notification(
        db,
        user_id=test_user.id,
        message="Test notification",
        link="/test"
    )

    assert notification.id is not None
    assert notification.user_id == test_user.id
    assert notification.message == "Test notification"
    assert notification.link == "/test"
    assert notification.read == 0


def test_get_unread_notifications(db, test_user):
    """Test retrieving unread notifications."""
    # Create some notifications
    create_notification(db, test_user.id, "Notification 1", "/link1")
    create_notification(db, test_user.id, "Notification 2", "/link2")

    # Create a read notification
    notification3 = create_notification(db, test_user.id, "Notification 3", "/link3")
    notification3.read = 1
    db.commit()

    # Get unread notifications
    unread = get_unread_notifications(db, test_user.id)

    assert len(unread) == 2
    assert all(n.read == 0 for n in unread)


def test_mark_notification_as_read(db, test_user):
    """Test marking a notification as read."""
    notification = create_notification(db, test_user.id, "Test", "/test")

    assert notification.read == 0

    # Mark as read
    success = mark_notification_as_read(db, notification.id, test_user.id)

    assert success is True
    db.refresh(notification)
    assert notification.read == 1


def test_mark_notification_as_read_not_found(db, test_user):
    """Test marking non-existent notification as read."""
    success = mark_notification_as_read(db, 99999, test_user.id)
    assert success is False


def test_mark_notification_as_read_wrong_user(db, test_user, test_org):
    """Test that users can only mark their own notifications as read."""
    from src.app.models import User
    from src.app.auth import get_password_hash

    # Create another user
    user2 = User(
        email="user2@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="User 2",
        role="staff",
        organization_id=test_org.id
    )
    db.add(user2)
    db.commit()
    db.refresh(user2)

    # Create notification for test_user
    notification = create_notification(db, test_user.id, "Test", "/test")

    # Try to mark as read with user2
    success = mark_notification_as_read(db, notification.id, user2.id)

    assert success is False
    db.refresh(notification)
    assert notification.read == 0


def test_get_unread_count(db, test_user):
    """Test getting count of unread notifications."""
    # Initially zero
    assert get_unread_count(db, test_user.id) == 0

    # Create some notifications
    create_notification(db, test_user.id, "Notification 1")
    create_notification(db, test_user.id, "Notification 2")
    create_notification(db, test_user.id, "Notification 3")

    assert get_unread_count(db, test_user.id) == 3

    # Mark one as read
    notifications = get_unread_notifications(db, test_user.id)
    mark_notification_as_read(db, notifications[0].id, test_user.id)

    assert get_unread_count(db, test_user.id) == 2


def test_check_request_reminders_approaching_due(db, test_user):
    """Test notifications for requests approaching due date."""
    # Create a request due in 5 days
    due_date = date.today() + timedelta(days=5)
    request = AccessRequest(
        requester_name="John Doe",
        requester_email="john@example.com",
        request_type=RequestType.ACCESS,
        description="Test request",
        status=AccessRequestStatus.RECEIVED,
        due_date=due_date,
        organization_id=test_user.organization_id
    )
    db.add(request)
    db.commit()

    # Check for reminders
    notifications = check_and_create_request_reminders(db, test_user.organization_id)

    assert len(notifications) > 0
    assert any("John Doe" in n.message for n in notifications)
    assert any("due in 5 day(s)" in n.message for n in notifications)


def test_check_request_reminders_no_notification_for_completed(db, test_user):
    """Test that completed requests don't generate notifications."""
    # Create a completed request due in 5 days
    due_date = date.today() + timedelta(days=5)
    request = AccessRequest(
        requester_name="Jane Doe",
        requester_email="jane@example.com",
        request_type=RequestType.CORRECTION,
        description="Test request",
        status=AccessRequestStatus.COMPLETED,
        due_date=due_date,
        organization_id=test_user.organization_id
    )
    db.add(request)
    db.commit()

    # Check for reminders
    notifications = check_and_create_request_reminders(db, test_user.organization_id)

    assert len(notifications) == 0


def test_check_request_reminders_no_duplicate(db, test_user):
    """Test that duplicate notifications are not created within 24 hours."""
    # Create a request due in 5 days
    due_date = date.today() + timedelta(days=5)
    request = AccessRequest(
        requester_name="John Doe",
        requester_email="john@example.com",
        request_type=RequestType.ACCESS,
        description="Test request",
        status=AccessRequestStatus.RECEIVED,
        due_date=due_date,
        organization_id=test_user.organization_id
    )
    db.add(request)
    db.commit()

    # Check for reminders twice
    notifications1 = check_and_create_request_reminders(db, test_user.organization_id)
    notifications2 = check_and_create_request_reminders(db, test_user.organization_id)

    assert len(notifications1) > 0
    assert len(notifications2) == 0  # No duplicates


def test_check_pia_reminders_stale_review(db, test_user):
    """Test notifications for PIAs in review for more than 14 days."""
    # Create a PIA that has been in review for 15 days
    old_date = datetime.now(timezone.utc) - timedelta(days=15)
    pia = PIA(
        title="Test PIA",
        description="Test description",
        data_types=["names", "addresses"],
        data_flow_description="Test flow",
        risk_level=RiskLevel.MEDIUM,
        mitigation_measures="Test measures",
        status=PIAStatus.IN_REVIEW,
        organization_id=test_user.organization_id,
        created_by=test_user.id,
        updated_at=old_date
    )
    db.add(pia)
    db.commit()

    # Check for reminders
    notifications = check_and_create_pia_reminders(db, test_user.organization_id)

    assert len(notifications) > 0
    assert any("Test PIA" in n.message for n in notifications)
    assert any("15 days" in n.message for n in notifications)


def test_check_pia_reminders_no_notification_for_recent(db, test_user):
    """Test that recently updated PIAs don't generate notifications."""
    # Create a PIA updated 7 days ago
    recent_date = datetime.now(timezone.utc) - timedelta(days=7)
    pia = PIA(
        title="Recent PIA",
        description="Test description",
        data_types=["names"],
        data_flow_description="Test flow",
        risk_level=RiskLevel.LOW,
        mitigation_measures="Test measures",
        status=PIAStatus.IN_REVIEW,
        organization_id=test_user.organization_id,
        created_by=test_user.id,
        updated_at=recent_date
    )
    db.add(pia)
    db.commit()

    # Check for reminders
    notifications = check_and_create_pia_reminders(db, test_user.organization_id)

    assert len(notifications) == 0


def test_check_ipp_reminders_non_compliant(db, test_user):
    """Test notifications for non-compliant IPP assessments."""
    # Create a non-compliant IPP assessment
    assessment = IPPAssessment(
        ipp_number=1,
        ipp_name="Collection",
        compliance_status=ComplianceStatus.NON_COMPLIANT,
        evidence_notes="Needs improvement",
        organization_id=test_user.organization_id
    )
    db.add(assessment)
    db.commit()

    # Check for reminders
    notifications = check_and_create_ipp_reminders(db, test_user.organization_id)

    assert len(notifications) > 0
    assert any("IPP 1" in n.message for n in notifications)
    assert any("non-compliant" in n.message for n in notifications)


def test_check_ipp_reminders_no_notification_for_compliant(db, test_user):
    """Test that compliant IPPs don't generate notifications."""
    # Create a compliant IPP assessment
    assessment = IPPAssessment(
        ipp_number=2,
        ipp_name="Use and Disclosure",
        compliance_status=ComplianceStatus.COMPLIANT,
        evidence_notes="All good",
        organization_id=test_user.organization_id
    )
    db.add(assessment)
    db.commit()

    # Check for reminders
    notifications = check_and_create_ipp_reminders(db, test_user.organization_id)

    assert len(notifications) == 0


def test_check_breach_reminders_requiring_action(db, test_user):
    """Test notifications for breach incidents requiring action."""
    # Create a breach incident in detected status
    incident = BreachIncident(
        title="Test Breach",
        description="Test breach incident",
        severity=RiskLevel.HIGH,
        date_discovered=datetime.now(timezone.utc),
        affected_records_count=100,
        data_types_affected=["names", "emails"],
        status=BreachIncidentStatus.DETECTED,
        organization_id=test_user.organization_id
    )
    db.add(incident)
    db.commit()

    # Check for reminders
    notifications = check_and_create_breach_reminders(db, test_user.organization_id)

    assert len(notifications) > 0
    assert any("Test Breach" in n.message for n in notifications)
    assert any("requires action" in n.message for n in notifications)


def test_check_breach_reminders_no_notification_for_resolved(db, test_user):
    """Test that resolved breaches don't generate notifications."""
    # Create a resolved breach incident
    incident = BreachIncident(
        title="Resolved Breach",
        description="Already resolved",
        severity=RiskLevel.LOW,
        date_discovered=datetime.now(timezone.utc) - timedelta(days=5),
        affected_records_count=10,
        data_types_affected=["names"],
        status=BreachIncidentStatus.RESOLVED,
        organization_id=test_user.organization_id
    )
    db.add(incident)
    db.commit()

    # Check for reminders
    notifications = check_and_create_breach_reminders(db, test_user.organization_id)

    assert len(notifications) == 0


def test_check_all_reminders(db, test_user):
    """Test checking all reminder types at once."""
    # Create various items requiring notifications

    # Request due in 5 days
    request = AccessRequest(
        requester_name="John Doe",
        requester_email="john@example.com",
        request_type=RequestType.ACCESS,
        description="Test request",
        status=AccessRequestStatus.RECEIVED,
        due_date=date.today() + timedelta(days=5),
        organization_id=test_user.organization_id
    )
    db.add(request)

    # Stale PIA
    old_date = datetime.now(timezone.utc) - timedelta(days=15)
    pia = PIA(
        title="Stale PIA",
        description="Test",
        data_types=["names"],
        data_flow_description="Test",
        risk_level=RiskLevel.LOW,
        mitigation_measures="Test",
        status=PIAStatus.IN_REVIEW,
        organization_id=test_user.organization_id,
        created_by=test_user.id,
        updated_at=old_date
    )
    db.add(pia)

    # Non-compliant IPP
    assessment = IPPAssessment(
        ipp_number=3,
        ipp_name="Data Quality",
        compliance_status=ComplianceStatus.NON_COMPLIANT,
        evidence_notes="Needs work",
        organization_id=test_user.organization_id
    )
    db.add(assessment)

    # Active breach
    incident = BreachIncident(
        title="Active Breach",
        description="Needs attention",
        severity=RiskLevel.HIGH,
        date_discovered=datetime.now(timezone.utc),
        affected_records_count=50,
        data_types_affected=["names"],
        status=BreachIncidentStatus.INVESTIGATING,
        organization_id=test_user.organization_id
    )
    db.add(incident)

    db.commit()

    # Check all reminders
    result = check_and_create_all_reminders(db, test_user.organization_id)

    assert len(result['request_reminders']) > 0
    assert len(result['pia_reminders']) > 0
    assert len(result['ipp_reminders']) > 0
    assert len(result['breach_reminders']) > 0


def test_api_get_notifications_unauthenticated(client):
    """Test GET /api/notifications requires authentication."""
    response = client.get("/api/notifications")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_api_get_notifications_authenticated(client, db, test_user):
    """Test GET /api/notifications returns notifications."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create some notifications
    create_notification(db, test_user.id, "Test notification 1", "/link1")
    create_notification(db, test_user.id, "Test notification 2", "/link2")

    # Get notifications
    response = client.get("/api/notifications")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "notifications" in data
    assert "count" in data
    assert data["count"] >= 2
    assert any(n["message"] == "Test notification 1" for n in data["notifications"])


def test_api_mark_notification_read(client, db, test_user):
    """Test POST /api/notifications/{id}/read marks notification as read."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create notification
    notification = create_notification(db, test_user.id, "Test notification", "/test")

    # Mark as read
    response = client.post(f"/api/notifications/{notification.id}/read")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "ok"

    # Verify notification is marked as read
    db.refresh(notification)
    assert notification.read == 1


def test_api_mark_notification_read_not_found(client, test_user):
    """Test marking non-existent notification returns 404."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Try to mark non-existent notification as read
    response = client.post("/api/notifications/99999/read")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_api_get_notification_count(client, db, test_user):
    """Test GET /api/notifications/count returns count."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create notifications
    create_notification(db, test_user.id, "Notification 1")
    create_notification(db, test_user.id, "Notification 2")
    create_notification(db, test_user.id, "Notification 3")

    # Get count
    response = client.get("/api/notifications/count")
    assert response.status_code == status.HTTP_200_OK

    count_text = response.text.strip()
    # The count should be at least 3
    assert int(count_text) >= 3


def test_notification_bell_in_base_template(client, test_user):
    """Test that notification bell appears in the base template."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access any authenticated page
    response = client.get("/dashboard")
    assert response.status_code == status.HTTP_200_OK

    content = response.content.decode()
    assert "notification-bell" in content
    assert "notification-badge" in content
    assert "notification-dropdown" in content
    assert "/api/notifications" in content


def test_multi_tenant_notification_isolation(client, db, test_org, test_user):
    """Test that users only see notifications for their organization."""
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

    # Create notifications for both users
    create_notification(db, test_user.id, "Notification for user 1", "/link1")
    create_notification(db, user2.id, "Notification for user 2", "/link2")

    # Login as first user
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Get notifications
    response = client.get("/api/notifications")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    messages = [n["message"] for n in data["notifications"]]

    # Should see own notifications but not other user's
    assert any("user 1" in msg for msg in messages)
    assert not any("user 2" in msg for msg in messages)
