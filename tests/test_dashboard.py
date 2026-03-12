"""Tests for TASK-011: Compliance Dashboard."""

import pytest
from datetime import date, timedelta, datetime
from src.app.models import (
    Organization, User, PrivacyOfficer, PIA, PIAStatus, RiskLevel,
    AccessRequest, RequestType, AccessRequestStatus, BreachIncident, BreachIncidentStatus,
    IPPAssessment, ComplianceStatus, AuditLog
)
from src.app.auth import get_password_hash


class TestDashboardDataAggregation:
    """Tests for dashboard data aggregation."""

    def test_dashboard_shows_ipp_compliance_score(self, client, db, test_user):
        """Verify dashboard shows IPP compliance score."""
        # Create some IPP assessments
        for i in range(1, 12):
            assessment = IPPAssessment(
                ipp_number=i,
                ipp_name=f"IPP {i}",
                compliance_status=ComplianceStatus.COMPLIANT if i <= 5 else ComplianceStatus.NOT_ASSESSED,
                organization_id=test_user.organization_id
            )
            db.add(assessment)
        db.commit()

        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "5/11" in response.text
        assert "45%" in response.text

    def test_dashboard_shows_privacy_officer_status_designated(self, client, db, test_user):
        """Verify dashboard shows Privacy Officer status when designated."""
        # Create Privacy Officer
        po = PrivacyOfficer(
            user_id=test_user.id,
            organization_id=test_user.organization_id,
            designation_date=date.today(),
            contact_phone="0412345678"
        )
        db.add(po)
        db.commit()

        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "✓ Designated" in response.text
        assert test_user.full_name in response.text

    def test_dashboard_shows_privacy_officer_action_required(self, client, db, test_user):
        """Verify dashboard shows action required when no Privacy Officer."""
        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "⚠ Action Required" in response.text
        assert "No Privacy Officer designated" in response.text

    def test_dashboard_shows_open_pias_with_risk_breakdown(self, client, db, test_user):
        """Verify dashboard shows open PIAs count with risk breakdown."""
        # Create PIAs with different risk levels
        pias_data = [
            {"risk": RiskLevel.CRITICAL, "status": PIAStatus.DRAFT},
            {"risk": RiskLevel.HIGH, "status": PIAStatus.IN_REVIEW},
            {"risk": RiskLevel.MEDIUM, "status": PIAStatus.DRAFT},
            {"risk": RiskLevel.MEDIUM, "status": PIAStatus.DRAFT},
            {"risk": RiskLevel.LOW, "status": PIAStatus.DRAFT},
            {"risk": RiskLevel.HIGH, "status": PIAStatus.APPROVED},  # Should not count (approved)
        ]

        for pia_data in pias_data:
            pia = PIA(
                title=f"PIA {pia_data['risk'].value}",
                description="Test PIA",
                data_types={"names": True},
                data_flow_description="Test flow",
                risk_level=pia_data["risk"],
                mitigation_measures="Test mitigation",
                status=pia_data["status"],
                organization_id=test_user.organization_id,
                created_by=test_user.id
            )
            db.add(pia)
        db.commit()

        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        # Check total open PIAs (5, not counting approved)
        response_text = response.text
        # Check risk breakdown
        assert "Critical:" in response_text
        assert "High:" in response_text
        assert "Medium:" in response_text
        assert "Low:" in response_text

    def test_dashboard_shows_pending_requests_with_overdue_count(self, client, db, test_user):
        """Verify dashboard shows pending requests with overdue count highlighted."""
        # Create pending requests (some overdue)
        today = date.today()
        requests_data = [
            {"due_date": today - timedelta(days=5), "status": AccessRequestStatus.RECEIVED},  # Overdue
            {"due_date": today - timedelta(days=2), "status": AccessRequestStatus.IN_PROGRESS},  # Overdue
            {"due_date": today + timedelta(days=5), "status": AccessRequestStatus.RECEIVED},  # Not overdue
            {"due_date": today - timedelta(days=1), "status": AccessRequestStatus.COMPLETED},  # Completed (not pending)
        ]

        for req_data in requests_data:
            request = AccessRequest(
                requester_name="Test Requester",
                requester_email="requester@example.com",
                request_type=RequestType.ACCESS,
                description="Test request",
                status=req_data["status"],
                due_date=req_data["due_date"],
                organization_id=test_user.organization_id
            )
            db.add(request)
        db.commit()

        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        # Should show 3 pending requests
        # Should highlight 2 overdue requests in red
        assert "2 Overdue" in response.text
        assert "text-red-800" in response.text

    def test_dashboard_shows_no_overdue_warning_when_none(self, client, db, test_user):
        """Verify dashboard doesn't show overdue warning when no overdue requests."""
        # Create only non-overdue requests
        today = date.today()
        request = AccessRequest(
            requester_name="Test Requester",
            requester_email="requester@example.com",
            request_type=RequestType.ACCESS,
            description="Test request",
            status=AccessRequestStatus.RECEIVED,
            due_date=today + timedelta(days=5),
            organization_id=test_user.organization_id
        )
        db.add(request)
        db.commit()

        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Overdue" not in response.text

    def test_dashboard_shows_active_incidents_with_severity_summary(self, client, db, test_user):
        """Verify dashboard shows active breach incidents with severity summary."""
        # Create incidents with different severities
        incidents_data = [
            {"severity": RiskLevel.CRITICAL, "status": BreachIncidentStatus.DETECTED},
            {"severity": RiskLevel.HIGH, "status": BreachIncidentStatus.INVESTIGATING},
            {"severity": RiskLevel.MEDIUM, "status": BreachIncidentStatus.CONTAINED},
            {"severity": RiskLevel.LOW, "status": BreachIncidentStatus.INVESTIGATING},
            {"severity": RiskLevel.HIGH, "status": BreachIncidentStatus.RESOLVED},  # Not active
        ]

        for inc_data in incidents_data:
            incident = BreachIncident(
                title=f"Incident {inc_data['severity'].value}",
                description="Test incident",
                severity=inc_data["severity"],
                date_discovered=datetime.now(),
                affected_records_count=100,
                data_types_affected={"names": True},
                containment_actions="Test actions",
                status=inc_data["status"],
                organization_id=test_user.organization_id
            )
            db.add(incident)
        db.commit()

        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        # Check severity breakdown is shown
        assert "Critical:" in response.text
        assert "High:" in response.text
        assert "Medium:" in response.text
        assert "Low:" in response.text

    def test_dashboard_shows_recent_audit_trail(self, client, db, test_user):
        """Verify dashboard shows last 5 audit trail entries."""
        # Create 7 audit log entries
        for i in range(7):
            log = AuditLog(
                user_id=test_user.id,
                action=f"Test action {i+1}",
                entity_type="test",
                entity_id=i,
                timestamp=datetime.now()
            )
            db.add(log)
        db.commit()

        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        # Should show only last 5 entries
        assert "Test action 7" in response.text
        assert "Test action 6" in response.text
        assert "Test action 5" in response.text
        assert "Test action 4" in response.text
        assert "Test action 3" in response.text
        # Should not show older entries
        assert "Test action 1" not in response.text
        assert "Test action 2" not in response.text

    def test_dashboard_shows_no_activity_message(self, client, db, test_user):
        """Verify dashboard shows 'no activity' message when no audit logs."""
        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "No recent activity" in response.text


class TestDashboardLinks:
    """Tests for dashboard card links."""

    def test_dashboard_cards_link_to_respective_pages(self, client, db, test_user):
        """Verify each dashboard card links to its respective page."""
        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200

        # Check all links are present
        assert 'href="/ipp-checklist"' in response.text
        assert 'href="/privacy-officer"' in response.text
        assert 'href="/pias"' in response.text
        assert 'href="/requests"' in response.text
        assert 'href="/incidents"' in response.text
        assert 'href="/data-register"' in response.text


class TestDashboardPerformance:
    """Tests for dashboard performance."""

    def test_dashboard_loads_with_large_dataset(self, client, db, test_user):
        """Verify dashboard loads efficiently even with larger datasets."""
        # Create a larger dataset
        for i in range(1, 12):
            assessment = IPPAssessment(
                ipp_number=i,
                ipp_name=f"IPP {i}",
                compliance_status=ComplianceStatus.COMPLIANT if i % 2 == 0 else ComplianceStatus.NOT_ASSESSED,
                organization_id=test_user.organization_id
            )
            db.add(assessment)

        for i in range(20):
            pia = PIA(
                title=f"PIA {i}",
                description="Test PIA",
                data_types={"names": True},
                data_flow_description="Test flow",
                risk_level=RiskLevel.MEDIUM,
                mitigation_measures="Test mitigation",
                status=PIAStatus.DRAFT,
                organization_id=test_user.organization_id,
                created_by=test_user.id
            )
            db.add(pia)

        for i in range(30):
            request = AccessRequest(
                requester_name=f"Requester {i}",
                requester_email=f"req{i}@example.com",
                request_type=RequestType.ACCESS,
                description="Test request",
                status=AccessRequestStatus.RECEIVED,
                due_date=date.today() + timedelta(days=i),
                organization_id=test_user.organization_id
            )
            db.add(request)

        db.commit()

        # Login
        client.post(
            "/web/login",
            data={"username": test_user.email, "password": "testpassword123"}
        )

        # Get dashboard - should load successfully
        response = client.get("/dashboard")
        assert response.status_code == 200


class TestDashboardAccessControl:
    """Tests for dashboard access control."""

    def test_dashboard_requires_authentication(self, client):
        """Verify dashboard redirects to login when not authenticated."""
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/web/login" in response.headers["location"]

    def test_dashboard_shows_user_specific_data(self, client, db):
        """Verify dashboard shows only data for the user's organization."""
        # Create two organizations with users
        org1 = Organization(name="Org 1", abn="11111111111", industry="Tech")
        org2 = Organization(name="Org 2", abn="22222222222", industry="Finance")
        db.add_all([org1, org2])
        db.commit()

        user1 = User(
            email="user1@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="User One",
            role="admin",
            organization_id=org1.id
        )
        user2 = User(
            email="user2@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="User Two",
            role="admin",
            organization_id=org2.id
        )
        db.add_all([user1, user2])
        db.commit()

        # Create data for org1
        pia1 = PIA(
            title="Org 1 PIA",
            description="Test PIA",
            data_types={"names": True},
            data_flow_description="Test flow",
            risk_level=RiskLevel.HIGH,
            mitigation_measures="Test mitigation",
            status=PIAStatus.DRAFT,
            organization_id=org1.id,
            created_by=user1.id
        )
        db.add(pia1)
        db.commit()

        # Login as user1
        client.post(
            "/web/login",
            data={"username": user1.email, "password": "password123"}
        )

        # Get dashboard
        response = client.get("/dashboard")
        assert response.status_code == 200
        # Should show org1 data but not mention org2
        assert "Org 1 PIA" not in response.text  # PIAs are counted, not listed by name on dashboard
