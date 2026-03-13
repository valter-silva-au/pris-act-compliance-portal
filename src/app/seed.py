"""Seed demo data for WA PRIS Act Compliance Portal."""

from datetime import datetime, timedelta, timezone, date
from sqlalchemy.orm import Session

from src.app.models import (
    Organization, User, PrivacyOfficer, IPPAssessment, PIA, DataRegister,
    AccessRequest, BreachIncident, OnboardingProgress,
    ComplianceStatus, PIAStatus, RiskLevel, RequestType,
    AccessRequestStatus, BreachIncidentStatus, UserRole
)
from src.app.auth import get_password_hash


def seed_demo_data(db: Session):
    """
    Populate database with demo data for testing.

    Creates:
    - 1 demo organization ("Acme IT Services")
    - 2 users (1 admin, 1 privacy officer)
    - 11 IPP assessments (7 compliant, 2 partial, 2 not assessed)
    - 2 PIAs (1 approved, 1 in draft)
    - 3 data register entries
    - 1 access request
    - 1 breach incident

    Args:
        db: Database session
    """
    # Check if demo org already exists
    existing_org = db.query(Organization).filter(
        Organization.abn == "12345678901"
    ).first()

    if existing_org:
        print("Demo data already exists. Skipping seed.")
        return

    print("Seeding demo data...")

    # 1. Create demo organization
    org = Organization(
        name="Acme IT Services",
        abn="12345678901",
        industry="Information Technology",
        number_of_employees=50,
        onboarding_completed=1,
        created_at=datetime.now(timezone.utc)
    )
    db.add(org)
    db.flush()  # Get org.id

    # 2. Create admin user
    admin_user = User(
        email="admin@demo.com",
        hashed_password=get_password_hash("demo1234"),
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        organization_id=org.id
    )
    db.add(admin_user)
    db.flush()  # Get admin_user.id

    # 3. Create privacy officer user
    po_user = User(
        email="privacy@demo.com",
        hashed_password=get_password_hash("demo1234"),
        full_name="Privacy Officer",
        role=UserRole.PRIVACY_OFFICER.value,
        organization_id=org.id
    )
    db.add(po_user)
    db.flush()  # Get po_user.id

    # 4. Create privacy officer profile
    po_profile = PrivacyOfficer(
        user_id=po_user.id,
        organization_id=org.id,
        designation_date=date.today() - timedelta(days=180),
        contact_phone="+61 8 9123 4567"
    )
    db.add(po_profile)

    # 5. Create onboarding progress (completed)
    onboarding = OnboardingProgress(
        organization_id=org.id,
        current_step=4,
        step1_completed=1,
        step2_completed=1,
        step3_completed=1,
        step4_completed=1,
        updated_at=datetime.now(timezone.utc)
    )
    db.add(onboarding)

    # 6. Create IPP assessments (7 compliant, 2 partial, 2 not assessed)
    ipp_data = [
        # IPP 1-7: Compliant
        (1, "Collection of personal information", ComplianceStatus.COMPLIANT,
         "We have clear policies for lawful collection of personal information directly from individuals."),
        (2, "Use and disclosure", ComplianceStatus.COMPLIANT,
         "Data is only used for stated purposes. Staff training completed on data usage policies."),
        (3, "Data quality", ComplianceStatus.COMPLIANT,
         "Regular data quality audits conducted. Processes in place to maintain accuracy."),
        (4, "Data security", ComplianceStatus.COMPLIANT,
         "Encryption in place for data at rest and in transit. Access controls implemented."),
        (5, "Openness", ComplianceStatus.COMPLIANT,
         "Privacy policy published on website and updated annually."),
        (6, "Access to personal information", ComplianceStatus.COMPLIANT,
         "Access request procedures documented and tested. Response times within required limits."),
        (7, "Correction of personal information", ComplianceStatus.COMPLIANT,
         "Correction request procedures in place. All corrections processed within 30 days."),

        # IPP 8-9: Partially compliant
        (8, "Accuracy of personal information before use", ComplianceStatus.PARTIAL,
         "Most data verified before use, but some legacy systems need improvement."),
        (9, "Use of government identifiers", ComplianceStatus.PARTIAL,
         "Working to phase out use of driver's license numbers. Expected completion Q2 2026."),

        # IPP 10-11: Not assessed yet
        (10, "Cross-border data transfer restrictions", ComplianceStatus.NOT_ASSESSED,
         ""),
        (11, "Sensitive information", ComplianceStatus.NOT_ASSESSED,
         ""),
    ]

    for ipp_num, ipp_name, status, evidence in ipp_data:
        assessment = IPPAssessment(
            ipp_number=ipp_num,
            ipp_name=ipp_name,
            compliance_status=status,
            evidence_notes=evidence,
            organization_id=org.id,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(assessment)

    # 7. Create 2 PIAs (1 approved, 1 in draft)
    pia1 = PIA(
        title="Customer Portal Migration to Cloud",
        description="Migration of customer data portal to AWS cloud infrastructure with enhanced security features.",
        data_types=["names", "addresses", "email", "financial"],
        data_flow_description="Customer data will be stored in AWS Sydney region with encryption at rest and in transit. Access via secure API endpoints only.",
        risk_level=RiskLevel.MEDIUM,
        mitigation_measures="- Use AWS KMS for encryption\n- Implement MFA for all admin access\n- Regular security audits\n- Data residency controls to keep data in Australia",
        status=PIAStatus.APPROVED,
        organization_id=org.id,
        created_by=admin_user.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=45),
        updated_at=datetime.now(timezone.utc) - timedelta(days=30)
    )
    db.add(pia1)

    pia2 = PIA(
        title="Employee Wellness Program",
        description="New wellness program collecting employee health data for insurance premium discounts.",
        data_types=["names", "health_info", "email"],
        data_flow_description="Health data collected via third-party wellness app and shared with insurance provider.",
        risk_level=RiskLevel.HIGH,
        mitigation_measures="- Obtain explicit consent from employees\n- Implement data minimization\n- Ensure insurance provider has adequate security",
        status=PIAStatus.DRAFT,
        organization_id=org.id,
        created_by=po_user.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=7),
        updated_at=datetime.now(timezone.utc) - timedelta(days=2)
    )
    db.add(pia2)

    # 8. Create 3 data register entries
    register1 = DataRegister(
        data_category="Customer Contact Information",
        description="Names, email addresses, phone numbers, and mailing addresses of current and prospective customers.",
        storage_location="CRM System (Salesforce), AWS Sydney region",
        access_controls="Role-based access. Sales and support staff only. MFA required.",
        retention_period="7 years after last contact, then archived for additional 3 years",
        legal_basis="Consent for marketing; legitimate business interest for customer service",
        date_last_reviewed=date.today() - timedelta(days=60),
        organization_id=org.id
    )
    db.add(register1)

    register2 = DataRegister(
        data_category="Employee HR Records",
        description="Employee personal details, employment history, performance reviews, salary information.",
        storage_location="HR Management System (BambooHR), encrypted database",
        access_controls="HR department only. Manager access limited to their direct reports.",
        retention_period="7 years after employment termination as per Fair Work Act",
        legal_basis="Employment contract and legal obligation",
        date_last_reviewed=date.today() - timedelta(days=90),
        organization_id=org.id
    )
    db.add(register2)

    register3 = DataRegister(
        data_category="Website Analytics Data",
        description="IP addresses, browser information, page views, session duration, referral sources.",
        storage_location="Google Analytics, cookies on user devices",
        access_controls="Marketing team access. Anonymized where possible.",
        retention_period="26 months, then automatically deleted",
        legal_basis="Legitimate interest (website improvement) with cookie consent",
        date_last_reviewed=date.today() - timedelta(days=30),
        organization_id=org.id
    )
    db.add(register3)

    # 9. Create 1 access request
    access_req = AccessRequest(
        requester_name="John Smith",
        requester_email="john.smith@example.com",
        request_type=RequestType.ACCESS,
        description="I am a former customer and would like to know what personal information you hold about me, how it is being used, and request a copy of all my data.",
        status=AccessRequestStatus.IN_PROGRESS,
        date_received=datetime.now(timezone.utc) - timedelta(days=5),
        due_date=date.today() + timedelta(days=25),  # 30-day response time
        assigned_handler_id=po_user.id,
        response_notes="Initial review completed. Gathering data from multiple systems.",
        date_completed=None,
        organization_id=org.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=5)
    )
    db.add(access_req)

    # 10. Create 1 breach incident
    breach = BreachIncident(
        title="Unauthorized Access to Test Database",
        description="An employee accidentally granted public read access to a test database containing anonymized but real customer data. Access was available for approximately 6 hours before being detected by automated security monitoring.",
        severity=RiskLevel.MEDIUM,
        date_discovered=datetime.now(timezone.utc) - timedelta(days=14),
        affected_records_count=1247,
        data_types_affected=["names", "email", "addresses"],
        containment_actions="- Immediate revocation of public access\n- Database access audit completed\n- Review of all test database configurations\n- Additional security training for development team\n- Enhanced monitoring rules deployed",
        status=BreachIncidentStatus.CONTAINED,
        notification_date=None,  # Not yet notified as risk assessment determined notification not required
        authority_notified=None,
        organization_id=org.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=14),
        updated_at=datetime.now(timezone.utc) - timedelta(days=10)
    )
    db.add(breach)

    # Commit all changes
    db.commit()

    print("Demo data seeded successfully!")
    print("\nDemo login credentials:")
    print("  Admin: admin@demo.com / demo1234")
    print("  Privacy Officer: privacy@demo.com / demo1234")
    print("\nOrganization: Acme IT Services (ABN: 12345678901)")
