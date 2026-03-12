"""Tests for database models."""

import pytest
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.database import Base, init_db
from src.app.models import (
    Organization, User, PrivacyOfficer, PIA, DataRegister,
    AccessRequest, BreachIncident, IPPAssessment, AuditLog,
    PIAStatus, RiskLevel, RequestType, AccessRequestStatus,
    BreachIncidentStatus, ComplianceStatus
)


@pytest.fixture
def test_db():
    """Create a test database in memory."""
    # Import models to ensure they're registered with Base before creating tables
    from src.app.models import (
        Organization, User, PrivacyOfficer, PIA, DataRegister,
        AccessRequest, BreachIncident, IPPAssessment, AuditLog
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def test_organization_creation(test_db):
    """Test creating an Organization model instance."""
    org = Organization(
        name="Test Organization",
        abn="12345678901",
        industry="Technology"
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)

    assert org.id is not None
    assert org.name == "Test Organization"
    assert org.abn == "12345678901"
    assert org.industry == "Technology"
    assert org.created_at is not None
    assert isinstance(org.created_at, datetime)


def test_user_creation(test_db):
    """Test creating a User model instance."""
    org = Organization(name="Test Org", abn="11111111111", industry="Tech")
    test_db.add(org)
    test_db.commit()

    user = User(
        email="test@example.com",
        hashed_password="hashed_password_123",
        full_name="Test User",
        role="admin",
        organization_id=org.id
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password_123"
    assert user.full_name == "Test User"
    assert user.role == "admin"
    assert user.organization_id == org.id
    assert user.organization.name == "Test Org"


def test_privacy_officer_creation(test_db):
    """Test creating a PrivacyOfficer model instance."""
    org = Organization(name="Test Org", abn="22222222222", industry="Healthcare")
    test_db.add(org)
    test_db.commit()

    user = User(
        email="officer@example.com",
        hashed_password="hashed_pass",
        full_name="Privacy Officer",
        role="privacy_officer",
        organization_id=org.id
    )
    test_db.add(user)
    test_db.commit()

    officer = PrivacyOfficer(
        user_id=user.id,
        organization_id=org.id,
        designation_date=date(2024, 1, 1),
        contact_phone="+61400000000"
    )
    test_db.add(officer)
    test_db.commit()
    test_db.refresh(officer)

    assert officer.id is not None
    assert officer.user_id == user.id
    assert officer.organization_id == org.id
    assert officer.designation_date == date(2024, 1, 1)
    assert officer.contact_phone == "+61400000000"
    assert officer.user.email == "officer@example.com"


def test_pia_creation(test_db):
    """Test creating a PIA model instance."""
    org = Organization(name="Test Org", abn="33333333333", industry="Finance")
    test_db.add(org)
    test_db.commit()

    user = User(
        email="creator@example.com",
        hashed_password="hashed_pass",
        full_name="PIA Creator",
        role="analyst",
        organization_id=org.id
    )
    test_db.add(user)
    test_db.commit()

    pia = PIA(
        title="Customer Data PIA",
        description="Privacy Impact Assessment for customer data processing",
        status=PIAStatus.DRAFT,
        risk_level=RiskLevel.MEDIUM,
        organization_id=org.id,
        created_by=user.id
    )
    test_db.add(pia)
    test_db.commit()
    test_db.refresh(pia)

    assert pia.id is not None
    assert pia.title == "Customer Data PIA"
    assert pia.description == "Privacy Impact Assessment for customer data processing"
    assert pia.status == PIAStatus.DRAFT
    assert pia.risk_level == RiskLevel.MEDIUM
    assert pia.organization_id == org.id
    assert pia.created_by == user.id
    assert pia.created_at is not None
    assert pia.updated_at is not None


def test_data_register_creation(test_db):
    """Test creating a DataRegister model instance."""
    org = Organization(name="Test Org", abn="44444444444", industry="Retail")
    test_db.add(org)
    test_db.commit()

    register = DataRegister(
        data_category="Customer PII",
        description="Personal identifiable information of customers",
        storage_location="AWS S3",
        access_controls="Role-based access control",
        retention_period="7 years",
        legal_basis="Contractual necessity",
        organization_id=org.id
    )
    test_db.add(register)
    test_db.commit()
    test_db.refresh(register)

    assert register.id is not None
    assert register.data_category == "Customer PII"
    assert register.storage_location == "AWS S3"
    assert register.retention_period == "7 years"
    assert register.organization_id == org.id


def test_access_request_creation(test_db):
    """Test creating an AccessRequest model instance."""
    org = Organization(name="Test Org", abn="55555555555", industry="Education")
    test_db.add(org)
    test_db.commit()

    request = AccessRequest(
        requester_name="John Doe",
        requester_email="john.doe@example.com",
        request_type=RequestType.ACCESS,
        description="Request to access my personal data",
        status=AccessRequestStatus.RECEIVED,
        due_date=date(2024, 6, 30),
        organization_id=org.id
    )
    test_db.add(request)
    test_db.commit()
    test_db.refresh(request)

    assert request.id is not None
    assert request.requester_name == "John Doe"
    assert request.requester_email == "john.doe@example.com"
    assert request.request_type == RequestType.ACCESS
    assert request.status == AccessRequestStatus.RECEIVED
    assert request.due_date == date(2024, 6, 30)
    assert request.created_at is not None


def test_breach_incident_creation(test_db):
    """Test creating a BreachIncident model instance."""
    org = Organization(name="Test Org", abn="66666666666", industry="Healthcare")
    test_db.add(org)
    test_db.commit()

    incident = BreachIncident(
        title="Data Breach Incident",
        description="Unauthorized access detected",
        severity=RiskLevel.HIGH,
        date_discovered=datetime(2024, 3, 1, 10, 30),
        date_reported=datetime(2024, 3, 2, 9, 0),
        affected_records_count=150,
        containment_actions="Disabled compromised accounts",
        status=BreachIncidentStatus.INVESTIGATING,
        organization_id=org.id
    )
    test_db.add(incident)
    test_db.commit()
    test_db.refresh(incident)

    assert incident.id is not None
    assert incident.title == "Data Breach Incident"
    assert incident.severity == RiskLevel.HIGH
    assert incident.affected_records_count == 150
    assert incident.status == BreachIncidentStatus.INVESTIGATING
    assert incident.created_at is not None


def test_ipp_assessment_creation(test_db):
    """Test creating an IPPAssessment model instance."""
    org = Organization(name="Test Org", abn="77777777777", industry="Government")
    test_db.add(org)
    test_db.commit()

    assessment = IPPAssessment(
        ipp_number=1,
        ipp_name="Collection",
        compliance_status=ComplianceStatus.COMPLIANT,
        evidence_notes="All data collection processes documented",
        organization_id=org.id
    )
    test_db.add(assessment)
    test_db.commit()
    test_db.refresh(assessment)

    assert assessment.id is not None
    assert assessment.ipp_number == 1
    assert assessment.ipp_name == "Collection"
    assert assessment.compliance_status == ComplianceStatus.COMPLIANT
    assert assessment.evidence_notes == "All data collection processes documented"
    assert assessment.updated_at is not None


def test_audit_log_creation(test_db):
    """Test creating an AuditLog model instance."""
    org = Organization(name="Test Org", abn="88888888888", industry="Legal")
    test_db.add(org)
    test_db.commit()

    user = User(
        email="auditor@example.com",
        hashed_password="hashed_pass",
        full_name="Auditor",
        role="admin",
        organization_id=org.id
    )
    test_db.add(user)
    test_db.commit()

    log = AuditLog(
        user_id=user.id,
        action="CREATE",
        entity_type="Organization",
        entity_id=org.id,
        details={"field": "name", "value": "Test Org"}
    )
    test_db.add(log)
    test_db.commit()
    test_db.refresh(log)

    assert log.id is not None
    assert log.user_id == user.id
    assert log.action == "CREATE"
    assert log.entity_type == "Organization"
    assert log.entity_id == org.id
    assert log.details == {"field": "name", "value": "Test Org"}
    assert log.timestamp is not None


def test_init_db():
    """Test that init_db creates all tables."""
    # Create a new in-memory database for this test
    from src.app.database import engine, Base

    # This should not raise any errors
    init_db()

    # Verify that tables were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    expected_tables = [
        "organizations", "users", "privacy_officers", "pias",
        "data_registers", "access_requests", "breach_incidents",
        "ipp_assessments", "audit_logs"
    ]

    for table in expected_tables:
        assert table in table_names


def test_model_relationships(test_db):
    """Test that model relationships work correctly."""
    org = Organization(name="Test Org", abn="99999999999", industry="Technology")
    test_db.add(org)
    test_db.commit()

    user = User(
        email="user@example.com",
        hashed_password="hashed_pass",
        full_name="Test User",
        role="admin",
        organization_id=org.id
    )
    test_db.add(user)
    test_db.commit()

    pia = PIA(
        title="Test PIA",
        description="Test description",
        status=PIAStatus.DRAFT,
        risk_level=RiskLevel.LOW,
        organization_id=org.id,
        created_by=user.id
    )
    test_db.add(pia)
    test_db.commit()

    # Test relationships
    assert len(org.users) == 1
    assert org.users[0].email == "user@example.com"
    assert len(org.pias) == 1
    assert org.pias[0].title == "Test PIA"
    assert user.organization.name == "Test Org"
    assert pia.creator.full_name == "Test User"


def test_enum_values():
    """Test that all enum values are correctly defined."""
    # Test PIAStatus enum
    assert PIAStatus.DRAFT.value == "draft"
    assert PIAStatus.IN_REVIEW.value == "in_review"
    assert PIAStatus.APPROVED.value == "approved"
    assert PIAStatus.REJECTED.value == "rejected"

    # Test RiskLevel enum
    assert RiskLevel.LOW.value == "low"
    assert RiskLevel.MEDIUM.value == "medium"
    assert RiskLevel.HIGH.value == "high"
    assert RiskLevel.CRITICAL.value == "critical"

    # Test RequestType enum
    assert RequestType.ACCESS.value == "access"
    assert RequestType.CORRECTION.value == "correction"

    # Test AccessRequestStatus enum
    assert AccessRequestStatus.RECEIVED.value == "received"
    assert AccessRequestStatus.IN_PROGRESS.value == "in_progress"
    assert AccessRequestStatus.COMPLETED.value == "completed"
    assert AccessRequestStatus.DENIED.value == "denied"

    # Test BreachIncidentStatus enum
    assert BreachIncidentStatus.DETECTED.value == "detected"
    assert BreachIncidentStatus.INVESTIGATING.value == "investigating"
    assert BreachIncidentStatus.CONTAINED.value == "contained"
    assert BreachIncidentStatus.RESOLVED.value == "resolved"
    assert BreachIncidentStatus.REPORTED.value == "reported"

    # Test ComplianceStatus enum
    assert ComplianceStatus.COMPLIANT.value == "compliant"
    assert ComplianceStatus.PARTIAL.value == "partial"
    assert ComplianceStatus.NON_COMPLIANT.value == "non_compliant"
    assert ComplianceStatus.NOT_ASSESSED.value == "not_assessed"
