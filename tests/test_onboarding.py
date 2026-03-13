"""Tests for onboarding wizard functionality."""

import pytest
from src.app.models import Organization, User, OnboardingProgress, PrivacyOfficer, IPPAssessment, ComplianceStatus


def test_new_user_sees_onboarding_after_login(client, db):
    """Test that new users are redirected to onboarding after first login."""
    # Create organization and user
    org = Organization(
        name="New Test Org",
        abn="11111111111",
        onboarding_completed=0
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="newuser@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="New User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "newuser@example.com", "password": "password123"},
        follow_redirects=False
    )

    # Should redirect to onboarding
    assert response.status_code == 302
    assert response.headers["location"] == "/onboarding"


def test_completed_user_skips_onboarding(client, db):
    """Test that users with completed onboarding go directly to dashboard."""
    # Create organization with onboarding completed
    org = Organization(
        name="Existing Org",
        abn="22222222222",
        onboarding_completed=1
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="existing@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Existing User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "existing@example.com", "password": "password123"},
        follow_redirects=False
    )

    # Should redirect to dashboard
    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"


def test_onboarding_page_requires_auth(client):
    """Test that onboarding page requires authentication."""
    response = client.get("/onboarding", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/web/login"


def test_onboarding_displays_wizard(client, db):
    """Test that onboarding page displays the wizard."""
    # Create organization and user
    org = Organization(
        name="Test Org",
        abn="33333333333",
        onboarding_completed=0
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="testuser@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Login
    login_response = client.post(
        "/web/login",
        data={"username": "testuser@example.com", "password": "password123"},
        follow_redirects=True
    )

    # Get onboarding page
    response = client.get("/onboarding")
    assert response.status_code == 200
    assert b"Welcome, Test Org!" in response.content
    assert b"Step 1: Organization Details" in response.content


def test_onboarding_step1_saves_organization_details(client, db):
    """Test that step 1 saves organization details."""
    # Create organization and user
    org = Organization(
        name="Test Org",
        abn="44444444444",
        onboarding_completed=0
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="step1test@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Step 1 User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Login
    client.post(
        "/web/login",
        data={"username": "step1test@example.com", "password": "password123"}
    )

    # Submit step 1
    response = client.post(
        "/onboarding/step-1",
        data={
            "abn": "55555555555",
            "industry": "Technology",
            "number_of_employees": 50
        }
    )

    assert response.status_code == 200
    assert b"Step 2: Designate Privacy Officer" in response.content

    # Verify data was saved
    db.refresh(org)
    assert org.abn == "55555555555"
    assert org.industry == "Technology"
    assert org.number_of_employees == 50

    # Check progress
    progress = db.query(OnboardingProgress).filter(
        OnboardingProgress.organization_id == org.id
    ).first()
    assert progress is not None
    assert progress.step1_completed == 1
    assert progress.current_step == 2


def test_onboarding_step2_creates_privacy_officer(client, db):
    """Test that step 2 creates a privacy officer."""
    # Create organization and user
    org = Organization(
        name="Test Org",
        abn="66666666666",
        onboarding_completed=0
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="step2test@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Step 2 User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Create progress at step 2
    progress = OnboardingProgress(
        organization_id=org.id,
        current_step=2,
        step1_completed=1
    )
    db.add(progress)
    db.commit()

    # Login
    client.post(
        "/web/login",
        data={"username": "step2test@example.com", "password": "password123"}
    )

    # Submit step 2 with existing user
    response = client.post(
        "/onboarding/step-2",
        data={
            "privacy_officer_type": "existing",
            "existing_user_id": str(user.id),
            "contact_phone": "+61400000000"
        }
    )

    assert response.status_code == 200
    assert b"Step 3: Initial IPP Self-Assessment" in response.content

    # Verify privacy officer was created
    po = db.query(PrivacyOfficer).filter(
        PrivacyOfficer.organization_id == org.id
    ).first()
    assert po is not None
    assert po.user_id == user.id
    assert po.contact_phone == "+61400000000"

    # Check progress
    db.refresh(progress)
    assert progress.step2_completed == 1
    assert progress.current_step == 3


def test_onboarding_step2_creates_new_user_as_privacy_officer(client, db):
    """Test that step 2 can create a new user as privacy officer."""
    # Create organization and user
    org = Organization(
        name="Test Org",
        abn="77777777777",
        onboarding_completed=0
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="step2new@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Step 2 New User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Create progress at step 2
    progress = OnboardingProgress(
        organization_id=org.id,
        current_step=2,
        step1_completed=1
    )
    db.add(progress)
    db.commit()

    # Login
    client.post(
        "/web/login",
        data={"username": "step2new@example.com", "password": "password123"}
    )

    # Submit step 2 with new user
    response = client.post(
        "/onboarding/step-2",
        data={
            "privacy_officer_type": "new",
            "new_po_name": "Jane Privacy Officer",
            "new_po_email": "jane.po@example.com",
            "contact_phone": "+61411111111"
        }
    )

    assert response.status_code == 200

    # Verify new user was created
    new_user = db.query(User).filter(User.email == "jane.po@example.com").first()
    assert new_user is not None
    assert new_user.full_name == "Jane Privacy Officer"
    assert new_user.role == "privacy_officer"

    # Verify privacy officer record was created
    po = db.query(PrivacyOfficer).filter(
        PrivacyOfficer.organization_id == org.id
    ).first()
    assert po is not None
    assert po.user_id == new_user.id


def test_onboarding_step3_saves_ipp_assessments(client, db):
    """Test that step 3 saves IPP assessments."""
    # Create organization and user
    org = Organization(
        name="Test Org",
        abn="88888888888",
        onboarding_completed=0
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="step3test@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Step 3 User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Create progress at step 3
    progress = OnboardingProgress(
        organization_id=org.id,
        current_step=3,
        step1_completed=1,
        step2_completed=1
    )
    db.add(progress)
    db.commit()

    # Login
    client.post(
        "/web/login",
        data={"username": "step3test@example.com", "password": "password123"}
    )

    # Submit step 3 with some IPPs marked as compliant
    form_data = {
        "ipp_1": "yes",
        "ipp_2": "yes",
        "ipp_3": "no",
        "ipp_4": "yes",
        "ipp_5": "no",
        "ipp_6": "yes",
        "ipp_7": "yes",
        "ipp_8": "no",
        "ipp_9": "yes",
        "ipp_10": "no",
        "ipp_11": "yes"
    }

    response = client.post("/onboarding/step-3", data=form_data)

    assert response.status_code == 200
    assert b"Step 4: Onboarding Complete" in response.content

    # Verify IPP assessments were created
    assessments = db.query(IPPAssessment).filter(
        IPPAssessment.organization_id == org.id
    ).all()
    assert len(assessments) == 11

    # Check some specific assessments
    ipp1 = next(a for a in assessments if a.ipp_number == 1)
    assert ipp1.compliance_status == ComplianceStatus.COMPLIANT

    ipp3 = next(a for a in assessments if a.ipp_number == 3)
    assert ipp3.compliance_status == ComplianceStatus.NOT_ASSESSED

    # Check progress
    db.refresh(progress)
    assert progress.step3_completed == 1
    assert progress.current_step == 4


def test_onboarding_complete_marks_organization_as_complete(client, db):
    """Test that completing onboarding marks the organization as complete."""
    # Create organization and user
    org = Organization(
        name="Test Org",
        abn="99999999999",
        onboarding_completed=0
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="complete@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Complete User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Create progress at step 4
    progress = OnboardingProgress(
        organization_id=org.id,
        current_step=4,
        step1_completed=1,
        step2_completed=1,
        step3_completed=1
    )
    db.add(progress)
    db.commit()

    # Login
    client.post(
        "/web/login",
        data={"username": "complete@example.com", "password": "password123"}
    )

    # Complete onboarding
    response = client.post("/onboarding/complete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    # Verify organization is marked as complete
    db.refresh(org)
    assert org.onboarding_completed == 1

    # Verify progress
    db.refresh(progress)
    assert progress.step4_completed == 1


def test_onboarding_wizard_navigation_back(client, db):
    """Test that users can navigate back through the wizard."""
    # Create organization and user
    org = Organization(
        name="Test Org",
        abn="10101010101",
        onboarding_completed=0
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="navtest@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Nav User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Create progress at step 3
    progress = OnboardingProgress(
        organization_id=org.id,
        current_step=3,
        step1_completed=1,
        step2_completed=1
    )
    db.add(progress)
    db.commit()

    # Login
    client.post(
        "/web/login",
        data={"username": "navtest@example.com", "password": "password123"}
    )

    # Navigate back to step 2
    response = client.get("/onboarding/back/2")

    assert response.status_code == 200
    assert b"Step 2: Designate Privacy Officer" in response.content

    # Check progress was updated
    db.refresh(progress)
    assert progress.current_step == 2


def test_completed_onboarding_redirects_to_dashboard(client, db):
    """Test that accessing onboarding with completed status redirects to dashboard."""
    # Create organization with completed onboarding
    org = Organization(
        name="Completed Org",
        abn="12121212121",
        onboarding_completed=1
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    from src.app.auth import get_password_hash
    user = User(
        email="redirecttest@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Redirect User",
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Login
    client.post(
        "/web/login",
        data={"username": "redirecttest@example.com", "password": "password123"}
    )

    # Try to access onboarding
    response = client.get("/onboarding", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"
