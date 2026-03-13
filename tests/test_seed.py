"""Tests for seed demo data functionality."""

import pytest
from src.app.seed import seed_demo_data
from src.app.models import (
    Organization, User, PrivacyOfficer, IPPAssessment, PIA, DataRegister,
    AccessRequest, BreachIncident, OnboardingProgress,
    ComplianceStatus, PIAStatus, AccessRequestStatus, BreachIncidentStatus
)
from src.app.auth import authenticate_user


class TestSeedDemoData:
    """Test seed demo data functionality."""

    def test_seed_creates_demo_organization(self, db):
        """Test that seed creates the demo organization."""
        seed_demo_data(db)

        org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()

        assert org is not None
        assert org.name == "Acme IT Services"
        assert org.industry == "Information Technology"
        assert org.number_of_employees == 50
        assert org.onboarding_completed == 1

    def test_seed_creates_admin_user(self, db):
        """Test that seed creates admin user with correct credentials."""
        seed_demo_data(db)

        admin = db.query(User).filter(User.email == "admin@demo.com").first()

        assert admin is not None
        assert admin.full_name == "Admin User"
        assert admin.role == "admin"

        # Verify login works
        auth_user = authenticate_user(db, "admin@demo.com", "demo1234")
        assert auth_user is not None
        assert auth_user.id == admin.id

    def test_seed_creates_privacy_officer_user(self, db):
        """Test that seed creates privacy officer user."""
        seed_demo_data(db)

        po = db.query(User).filter(User.email == "privacy@demo.com").first()

        assert po is not None
        assert po.full_name == "Privacy Officer"
        assert po.role == "privacy_officer"

        # Verify login works
        auth_user = authenticate_user(db, "privacy@demo.com", "demo1234")
        assert auth_user is not None

    def test_seed_creates_privacy_officer_profile(self, db):
        """Test that seed creates privacy officer profile."""
        seed_demo_data(db)

        org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()
        po_profile = db.query(PrivacyOfficer).filter(
            PrivacyOfficer.organization_id == org.id
        ).first()

        assert po_profile is not None
        assert po_profile.contact_phone == "+61 8 9123 4567"

    def test_seed_creates_11_ipp_assessments(self, db):
        """Test that seed creates all 11 IPP assessments."""
        seed_demo_data(db)

        org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()
        assessments = db.query(IPPAssessment).filter(
            IPPAssessment.organization_id == org.id
        ).all()

        assert len(assessments) == 11

        # Verify IPP numbers 1-11 are all present
        ipp_numbers = sorted([a.ipp_number for a in assessments])
        assert ipp_numbers == list(range(1, 12))

    def test_seed_ipp_compliance_distribution(self, db):
        """Test that IPPs have correct compliance status distribution."""
        seed_demo_data(db)

        org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()
        assessments = db.query(IPPAssessment).filter(
            IPPAssessment.organization_id == org.id
        ).all()

        compliant = [a for a in assessments if a.compliance_status == ComplianceStatus.COMPLIANT]
        partial = [a for a in assessments if a.compliance_status == ComplianceStatus.PARTIAL]
        not_assessed = [a for a in assessments if a.compliance_status == ComplianceStatus.NOT_ASSESSED]

        assert len(compliant) == 7
        assert len(partial) == 2
        assert len(not_assessed) == 2

    def test_seed_creates_2_pias(self, db):
        """Test that seed creates 2 PIAs with different statuses."""
        seed_demo_data(db)

        org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()
        pias = db.query(PIA).filter(PIA.organization_id == org.id).all()

        assert len(pias) == 2

        # Check statuses
        statuses = [p.status for p in pias]
        assert PIAStatus.APPROVED in statuses
        assert PIAStatus.DRAFT in statuses

    def test_seed_creates_3_data_register_entries(self, db):
        """Test that seed creates 3 data register entries."""
        seed_demo_data(db)

        org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()
        registers = db.query(DataRegister).filter(
            DataRegister.organization_id == org.id
        ).all()

        assert len(registers) == 3

        # Verify they have different categories
        categories = [r.data_category for r in registers]
        assert "Customer Contact Information" in categories
        assert "Employee HR Records" in categories
        assert "Website Analytics Data" in categories

    def test_seed_creates_1_access_request(self, db):
        """Test that seed creates 1 access request."""
        seed_demo_data(db)

        org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()
        requests = db.query(AccessRequest).filter(
            AccessRequest.organization_id == org.id
        ).all()

        assert len(requests) == 1

        req = requests[0]
        assert req.requester_name == "John Smith"
        assert req.requester_email == "john.smith@example.com"
        assert req.status == AccessRequestStatus.IN_PROGRESS

    def test_seed_creates_1_breach_incident(self, db):
        """Test that seed creates 1 breach incident."""
        seed_demo_data(db)

        org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()
        incidents = db.query(BreachIncident).filter(
            BreachIncident.organization_id == org.id
        ).all()

        assert len(incidents) == 1

        incident = incidents[0]
        assert incident.title == "Unauthorized Access to Test Database"
        assert incident.status == BreachIncidentStatus.CONTAINED
        assert incident.affected_records_count == 1247

    def test_seed_creates_onboarding_progress(self, db):
        """Test that seed creates completed onboarding progress."""
        seed_demo_data(db)

        org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()
        progress = db.query(OnboardingProgress).filter(
            OnboardingProgress.organization_id == org.id
        ).first()

        assert progress is not None
        assert progress.current_step == 4
        assert progress.step1_completed == 1
        assert progress.step2_completed == 1
        assert progress.step3_completed == 1
        assert progress.step4_completed == 1

    def test_seed_is_idempotent(self, db):
        """Test that seed can be run multiple times without errors."""
        seed_demo_data(db)
        seed_demo_data(db)  # Run again

        # Should still only have one demo org
        orgs = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).all()

        assert len(orgs) == 1

    def test_seed_data_scoped_to_demo_org(self, db):
        """Test that seed data is properly scoped to demo organization."""
        # Create a different organization first
        other_org = Organization(
            name="Other Organization",
            abn="98765432109",
            industry="Finance",
            onboarding_completed=1
        )
        db.add(other_org)
        db.commit()
        db.refresh(other_org)

        original_org_count = db.query(Organization).count()

        seed_demo_data(db)

        # Should have one more org (demo org)
        new_org_count = db.query(Organization).count()
        assert new_org_count == original_org_count + 1

        # Other org should not have any demo data
        other_org_ipps = db.query(IPPAssessment).filter(
            IPPAssessment.organization_id == other_org.id
        ).count()
        assert other_org_ipps == 0

        # Demo org should have all the data
        demo_org = db.query(Organization).filter(
            Organization.abn == "12345678901"
        ).first()
        demo_org_ipps = db.query(IPPAssessment).filter(
            IPPAssessment.organization_id == demo_org.id
        ).count()
        assert demo_org_ipps == 11
