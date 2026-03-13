"""Notification and reminder system for WA PRIS Act Compliance Portal."""

from datetime import date, timedelta, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List

from src.app.models import (
    Notification, User, AccessRequest, AccessRequestStatus,
    PIA, PIAStatus, IPPAssessment, ComplianceStatus,
    BreachIncident, BreachIncidentStatus
)


def create_notification(
    db: Session,
    user_id: int,
    message: str,
    link: str = None
) -> Notification:
    """
    Create a new notification for a user.

    Args:
        db: Database session
        user_id: ID of the user to notify
        message: Notification message
        link: Optional link to related resource

    Returns:
        Notification: The created notification
    """
    notification = Notification(
        user_id=user_id,
        message=message,
        link=link,
        read=0
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_unread_notifications(db: Session, user_id: int) -> List[Notification]:
    """
    Get all unread notifications for a user.

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        List[Notification]: List of unread notifications
    """
    return db.query(Notification).filter(
        and_(
            Notification.user_id == user_id,
            Notification.read == 0
        )
    ).order_by(Notification.created_at.desc()).all()


def mark_notification_as_read(db: Session, notification_id: int, user_id: int) -> bool:
    """
    Mark a notification as read.

    Args:
        db: Database session
        notification_id: ID of the notification
        user_id: ID of the user (for security)

    Returns:
        bool: True if notification was marked as read, False if not found
    """
    notification = db.query(Notification).filter(
        and_(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )
    ).first()

    if notification:
        notification.read = 1
        db.commit()
        return True
    return False


def get_unread_count(db: Session, user_id: int) -> int:
    """
    Get count of unread notifications for a user.

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        int: Count of unread notifications
    """
    return db.query(Notification).filter(
        and_(
            Notification.user_id == user_id,
            Notification.read == 0
        )
    ).count()


def check_and_create_request_reminders(db: Session, organization_id: int) -> List[Notification]:
    """
    Check for access/correction requests approaching due date (7 days before)
    and create notifications for users in the organization.

    Args:
        db: Database session
        organization_id: ID of the organization to check

    Returns:
        List[Notification]: List of created notifications
    """
    notifications_created = []

    # Calculate threshold date (7 days from now)
    threshold_date = date.today() + timedelta(days=7)

    # Find requests that are due within 7 days and not completed/denied
    requests = db.query(AccessRequest).filter(
        and_(
            AccessRequest.organization_id == organization_id,
            AccessRequest.due_date <= threshold_date,
            AccessRequest.due_date >= date.today(),
            AccessRequest.status.in_([AccessRequestStatus.RECEIVED, AccessRequestStatus.IN_PROGRESS])
        )
    ).all()

    if not requests:
        return notifications_created

    # Get all users in the organization (admins and privacy officers)
    users = db.query(User).filter(
        and_(
            User.organization_id == organization_id,
            User.role.in_(['admin', 'privacy_officer'])
        )
    ).all()

    for request in requests:
        days_until_due = (request.due_date - date.today()).days
        message = f"Access/Correction request from {request.requester_name} is due in {days_until_due} day(s)"
        link = "/requests"

        # Check if notification already exists for this request
        for user in users:
            # Use naive datetime for DB comparison
            cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
            existing = db.query(Notification).filter(
                and_(
                    Notification.user_id == user.id,
                    Notification.message == message,
                    Notification.created_at >= cutoff_time  # Don't duplicate within 24 hours
                )
            ).first()

            if not existing:
                notification = create_notification(db, user.id, message, link)
                notifications_created.append(notification)

    return notifications_created


def check_and_create_pia_reminders(db: Session, organization_id: int) -> List[Notification]:
    """
    Check for PIAs in review for more than 14 days and create notifications.

    Args:
        db: Database session
        organization_id: ID of the organization to check

    Returns:
        List[Notification]: List of created notifications
    """
    notifications_created = []

    # Calculate threshold date (14 days ago) - use naive datetime for DB comparison
    threshold_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=14)

    # Find PIAs in review for more than 14 days
    pias = db.query(PIA).filter(
        and_(
            PIA.organization_id == organization_id,
            PIA.status == PIAStatus.IN_REVIEW,
            PIA.updated_at <= threshold_date
        )
    ).all()

    if not pias:
        return notifications_created

    # Get all users in the organization (admins and privacy officers)
    users = db.query(User).filter(
        and_(
            User.organization_id == organization_id,
            User.role.in_(['admin', 'privacy_officer'])
        )
    ).all()

    for pia in pias:
        # Make pia.updated_at timezone-aware if it's naive
        updated_at = pia.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        days_in_review = (datetime.now(timezone.utc) - updated_at).days
        message = f"PIA '{pia.title}' has been in review for {days_in_review} days"
        link = f"/pias/{pia.id}"

        # Check if notification already exists for this PIA
        for user in users:
            # Use naive datetime for DB comparison
            cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
            existing = db.query(Notification).filter(
                and_(
                    Notification.user_id == user.id,
                    Notification.message == message,
                    Notification.created_at >= cutoff_time
                )
            ).first()

            if not existing:
                notification = create_notification(db, user.id, message, link)
                notifications_created.append(notification)

    return notifications_created


def check_and_create_ipp_reminders(db: Session, organization_id: int) -> List[Notification]:
    """
    Check for IPP assessment items marked as non-compliant and create notifications.

    Args:
        db: Database session
        organization_id: ID of the organization to check

    Returns:
        List[Notification]: List of created notifications
    """
    notifications_created = []

    # Find non-compliant IPP assessments
    assessments = db.query(IPPAssessment).filter(
        and_(
            IPPAssessment.organization_id == organization_id,
            IPPAssessment.compliance_status == ComplianceStatus.NON_COMPLIANT
        )
    ).all()

    if not assessments:
        return notifications_created

    # Get all users in the organization (admins and privacy officers)
    users = db.query(User).filter(
        and_(
            User.organization_id == organization_id,
            User.role.in_(['admin', 'privacy_officer'])
        )
    ).all()

    for assessment in assessments:
        message = f"IPP {assessment.ipp_number} ({assessment.ipp_name}) is marked as non-compliant"
        link = "/ipp-checklist"

        # Check if notification already exists for this assessment
        for user in users:
            # Use naive datetime for DB comparison
            cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
            existing = db.query(Notification).filter(
                and_(
                    Notification.user_id == user.id,
                    Notification.message == message,
                    Notification.created_at >= cutoff_time
                )
            ).first()

            if not existing:
                notification = create_notification(db, user.id, message, link)
                notifications_created.append(notification)

    return notifications_created


def check_and_create_breach_reminders(db: Session, organization_id: int) -> List[Notification]:
    """
    Check for breach incidents requiring action and create notifications.

    Args:
        db: Database session
        organization_id: ID of the organization to check

    Returns:
        List[Notification]: List of created notifications
    """
    notifications_created = []

    # Find breach incidents that require action (detected or investigating)
    incidents = db.query(BreachIncident).filter(
        and_(
            BreachIncident.organization_id == organization_id,
            BreachIncident.status.in_([BreachIncidentStatus.DETECTED, BreachIncidentStatus.INVESTIGATING])
        )
    ).all()

    if not incidents:
        return notifications_created

    # Get all users in the organization (admins and privacy officers)
    users = db.query(User).filter(
        and_(
            User.organization_id == organization_id,
            User.role.in_(['admin', 'privacy_officer'])
        )
    ).all()

    for incident in incidents:
        message = f"Breach incident '{incident.title}' requires action (Status: {incident.status.value})"
        link = f"/incidents/{incident.id}"

        # Check if notification already exists for this incident
        for user in users:
            # Use naive datetime for DB comparison
            cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
            existing = db.query(Notification).filter(
                and_(
                    Notification.user_id == user.id,
                    Notification.message == message,
                    Notification.created_at >= cutoff_time
                )
            ).first()

            if not existing:
                notification = create_notification(db, user.id, message, link)
                notifications_created.append(notification)

    return notifications_created


def check_and_create_all_reminders(db: Session, organization_id: int) -> dict:
    """
    Check all reminder conditions and create notifications as needed.

    Args:
        db: Database session
        organization_id: ID of the organization to check

    Returns:
        dict: Summary of notifications created by type
    """
    result = {
        'request_reminders': check_and_create_request_reminders(db, organization_id),
        'pia_reminders': check_and_create_pia_reminders(db, organization_id),
        'ipp_reminders': check_and_create_ipp_reminders(db, organization_id),
        'breach_reminders': check_and_create_breach_reminders(db, organization_id)
    }

    return result
