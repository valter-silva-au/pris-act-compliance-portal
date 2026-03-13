"""Tests for IPP compliance checklist endpoints."""

import pytest
from fastapi import status

from src.app.models import ComplianceStatus, IPPAssessment


class TestIPPInitialization:
    """Test IPP assessment initialization."""

    def test_initialize_creates_all_11_ipps(self, client, test_user, db):
        """Test that accessing IPP checklist initializes all 11 IPP assessments."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        response = client.get("/ipp-checklist")
        assert response.status_code == status.HTTP_200_OK
        assessments = db.query(IPPAssessment).filter(
            IPPAssessment.organization_id == test_user.organization_id
        ).all()
        assert len(assessments) == 11
        ipp_numbers = sorted([a.ipp_number for a in assessments])
        assert ipp_numbers == list(range(1, 12))
        for assessment in assessments:
            assert assessment.compliance_status == ComplianceStatus.NOT_ASSESSED
            assert assessment.ipp_name is not None
            assert assessment.ipp_name != ""

    def test_initialize_is_idempotent(self, client, test_user, db):
        """Test that multiple accesses don't create duplicate IPPs."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        client.get("/ipp-checklist")
        client.get("/ipp-checklist")
        client.get("/ipp-checklist")
        assessments = db.query(IPPAssessment).filter(
            IPPAssessment.organization_id == test_user.organization_id
        ).all()
        assert len(assessments) == 11


class TestIPPChecklistEndpoint:
    """Test GET /ipp-checklist endpoint."""

    def test_requires_authentication(self, client):
        """Test that IPP checklist requires authentication."""
        response = client.get("/ipp-checklist", follow_redirects=False)
        assert response.status_code == status.HTTP_302_FOUND
        assert response.headers["location"] == "/web/login"

    def test_returns_html_page(self, client, test_user):
        """Test that endpoint returns HTML page."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        response = client.get("/ipp-checklist")
        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    def test_displays_all_ipp_information(self, client, test_user):
        """Test that page displays all IPP information."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        response = client.get("/ipp-checklist")
        content = response.text
        assert "IPP Compliance Checklist" in content
        for i in range(1, 12):
            assert f"IPP {i}:" in content
        assert "Collection of personal information" in content
        assert "Use and disclosure" in content
        assert "Data security" in content
        assert "Sensitive information" in content
        assert "Overall Compliance Score" in content

    def test_displays_status_dropdowns(self, client, test_user):
        """Test that status dropdowns are displayed for each IPP."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        response = client.get("/ipp-checklist")
        content = response.text
        assert "Not Assessed" in content
        assert "Compliant" in content
        assert "Partially Compliant" in content
        assert "Non-Compliant" in content
        assert 'name="compliance_status"' in content


class TestUpdateIPPAssessment:
    """Test POST /api/ipp/{ipp_number} endpoint."""

    def test_requires_authentication(self, client):
        """Test that update endpoint requires authentication."""
        response = client.post("/api/ipp/1", json={"compliance_status": "compliant", "evidence_notes": "Test"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_updates_compliance_status(self, client, test_user, db):
        """Test that compliance status is updated in database."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        client.get("/ipp-checklist")
        update_data = {"compliance_status": "compliant", "evidence_notes": "We have implemented proper collection procedures"}
        response = client.post("/api/ipp/1", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        assessment = db.query(IPPAssessment).filter(
            IPPAssessment.organization_id == test_user.organization_id,
            IPPAssessment.ipp_number == 1
        ).first()
        assert assessment is not None
        assert assessment.compliance_status == ComplianceStatus.COMPLIANT
        assert assessment.evidence_notes == update_data["evidence_notes"]

    def test_returns_updated_score_html(self, client, test_user, db):
        """Test that endpoint returns updated compliance score HTML."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        client.get("/ipp-checklist")
        update_data = {"compliance_status": "compliant", "evidence_notes": "Test"}
        response = client.post("/api/ipp/1", json=update_data)
        content = response.text
        assert "Overall Compliance Score" in content
        assert "1/11" in content

    def test_invalid_ipp_number_returns_400(self, client, test_user):
        """Test that invalid IPP numbers return 400 error."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        update_data = {"compliance_status": "compliant", "evidence_notes": "Test"}
        response = client.post("/api/ipp/0", json=update_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response = client.post("/api/ipp/12", json=update_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestComplianceScoreCalculation:
    """Test compliance score calculation."""

    def test_score_updates_when_ipps_marked_compliant(self, client, test_user, db):
        """Test that compliance score updates as IPPs are marked compliant."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        client.get("/ipp-checklist")
        for i in range(1, 6):
            update_data = {"compliance_status": "compliant", "evidence_notes": f"Evidence for IPP {i}"}
            response = client.post(f"/api/ipp/{i}", json=update_data)
            content = response.text
            assert f"{i}/11" in content

    def test_score_shows_percentage(self, client, test_user):
        """Test that score includes percentage calculation."""
        login_data = {"username": test_user.email, "password": "testpassword123"}
        client.post("/web/login", data=login_data)
        client.get("/ipp-checklist")
        for i in range(1, 12):
            update_data = {"compliance_status": "compliant", "evidence_notes": f"Evidence for IPP {i}"}
            response = client.post(f"/api/ipp/{i}", json=update_data)
        content = response.text
        assert "11/11" in content
        assert "100" in content
