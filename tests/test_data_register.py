"""Tests for Data Register functionality."""

import pytest
from fastapi import status
from datetime import date
from src.app.models import DataRegister


def test_data_register_unauthenticated(client):
    """Test that unauthenticated users are redirected to login."""
    response = client.get("/data-register")
    assert response.status_code == status.HTTP_200_OK
    assert response.url.path == "/web/login"


def test_data_register_authenticated_empty(client, test_user):
    """Test data register page shows empty state when no entries exist."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access data register page
    response = client.get("/data-register", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"No Data Holdings Registered" in response.content


def test_data_register_authenticated_with_data(client, db, test_user):
    """Test data register page displays entries."""
    # Create a test data register entry
    entry = DataRegister(
        data_category="Employee Records",
        description="Personnel files and employment information",
        storage_location="HR Database Server",
        access_controls="HR Department only",
        retention_period="7 years after employment ends",
        legal_basis="Employment contract",
        date_last_reviewed=date(2026, 3, 1),
        organization_id=test_user.organization_id
    )
    db.add(entry)
    db.commit()

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Access data register page
    response = client.get("/data-register", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"Employee Records" in response.content
    assert b"HR Database Server" in response.content
    assert b"7 years after employment ends" in response.content
    assert b"2026-03-01" in response.content


def test_create_data_register_entry(client, db, test_user):
    """Test POST /api/data-register creates a new entry."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create data register entry
    response = client.post(
        "/api/data-register",
        data={
            "data_category": "Client Contact Details",
            "description": "Names, email addresses, phone numbers of clients",
            "storage_location": "CRM Database",
            "access_controls": "Sales and Support teams",
            "retention_period": "5 years after last contact",
            "legal_basis": "Consent for marketing communications",
            "date_last_reviewed": "2026-03-10"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/data-register"

    # Verify entry was created in database
    entry = db.query(DataRegister).filter(
        DataRegister.data_category == "Client Contact Details"
    ).first()
    assert entry is not None
    assert entry.description == "Names, email addresses, phone numbers of clients"
    assert entry.storage_location == "CRM Database"
    assert entry.access_controls == "Sales and Support teams"
    assert entry.retention_period == "5 years after last contact"
    assert entry.legal_basis == "Consent for marketing communications"
    assert entry.date_last_reviewed == date(2026, 3, 10)
    assert entry.organization_id == test_user.organization_id


def test_create_data_register_entry_minimal(client, db, test_user):
    """Test POST /api/data-register with only required fields."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Create data register entry with only category
    response = client.post(
        "/api/data-register",
        data={
            "data_category": "Minimal Entry",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER

    # Verify entry was created
    entry = db.query(DataRegister).filter(
        DataRegister.data_category == "Minimal Entry"
    ).first()
    assert entry is not None
    assert entry.description is None
    assert entry.storage_location is None
    assert entry.organization_id == test_user.organization_id


def test_update_data_register_entry(client, db, test_user):
    """Test POST /api/data-register/{id} updates an existing entry."""
    # Create a test entry
    entry = DataRegister(
        data_category="Original Category",
        description="Original description",
        storage_location="Original location",
        access_controls="Original access",
        retention_period="Original period",
        legal_basis="Original basis",
        date_last_reviewed=date(2026, 1, 1),
        organization_id=test_user.organization_id
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    original_id = entry.id

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Update entry
    response = client.post(
        f"/api/data-register/{entry.id}",
        data={
            "data_category": "Updated Category",
            "description": "Updated description",
            "storage_location": "Updated location",
            "access_controls": "Updated access",
            "retention_period": "Updated period",
            "legal_basis": "Updated basis",
            "date_last_reviewed": "2026-03-13"
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/data-register"

    # Verify entry was updated
    db.refresh(entry)
    assert entry.id == original_id
    assert entry.data_category == "Updated Category"
    assert entry.description == "Updated description"
    assert entry.storage_location == "Updated location"
    assert entry.access_controls == "Updated access"
    assert entry.retention_period == "Updated period"
    assert entry.legal_basis == "Updated basis"
    assert entry.date_last_reviewed == date(2026, 3, 13)


def test_update_data_register_entry_not_found(client, test_user):
    """Test updating non-existent entry returns 404."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Try to update non-existent entry
    response = client.post(
        "/api/data-register/99999",
        data={
            "data_category": "Test",
        },
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_data_register_entry(client, db, test_user):
    """Test DELETE /api/data-register/{id} removes an entry."""
    # Create a test entry
    entry = DataRegister(
        data_category="To Be Deleted",
        description="This will be deleted",
        organization_id=test_user.organization_id
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    entry_id = entry.id

    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Delete entry
    response = client.delete(f"/api/data-register/{entry_id}")
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    assert "deleted successfully" in json_response["message"]

    # Verify entry was deleted
    deleted_entry = db.query(DataRegister).filter(
        DataRegister.id == entry_id
    ).first()
    assert deleted_entry is None


def test_delete_data_register_entry_not_found(client, test_user):
    """Test deleting non-existent entry returns 404."""
    # Login first
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Try to delete non-existent entry
    response = client.delete("/api/data-register/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_data_register_entry_unauthenticated(client, db, test_user):
    """Test delete fails when not authenticated."""
    # Create a test entry
    entry = DataRegister(
        data_category="Test Entry",
        organization_id=test_user.organization_id
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Try to delete without authentication
    response = client.delete(f"/api/data-register/{entry.id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_multi_tenant_isolation(client, db, test_org, test_user):
    """Test that users can only see and modify entries from their own organization."""
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

    # Create entries for both organizations
    entry1 = DataRegister(
        data_category="Org 1 Data",
        description="Data for first org",
        organization_id=test_user.organization_id
    )
    entry2 = DataRegister(
        data_category="Org 2 Data",
        description="Data for second org",
        organization_id=org2.id
    )
    db.add(entry1)
    db.add(entry2)
    db.commit()
    db.refresh(entry1)
    db.refresh(entry2)

    # Login as first user
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Verify first user can see their entry but not the other
    response = client.get("/data-register", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK
    assert b"Org 1 Data" in response.content
    assert b"Org 2 Data" not in response.content

    # Verify first user cannot update second org's entry
    response = client.post(
        f"/api/data-register/{entry2.id}",
        data={"data_category": "Hacked"},
        follow_redirects=False
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Verify entry2 was not modified
    db.refresh(entry2)
    assert entry2.data_category == "Org 2 Data"

    # Verify first user cannot delete second org's entry
    response = client.delete(f"/api/data-register/{entry2.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Verify entry2 still exists
    db.refresh(entry2)
    assert entry2 is not None


def test_data_register_page_content(client, db, test_user):
    """Test that data register page contains required information."""
    # Create entries
    entry1 = DataRegister(
        data_category="Employee records",
        description="Full personnel files",
        storage_location="HR database",
        access_controls="HR Manager, HR Admin",
        retention_period="7 years",
        legal_basis="Employment Act",
        date_last_reviewed=date(2026, 2, 1),
        organization_id=test_user.organization_id
    )
    entry2 = DataRegister(
        data_category="Client contact details",
        description="Names and contact info",
        storage_location="Filing cabinet Room 3",
        access_controls="Sales team",
        retention_period="5 years",
        legal_basis="Consent",
        date_last_reviewed=None,  # Not reviewed
        organization_id=test_user.organization_id
    )
    db.add(entry1)
    db.add(entry2)
    db.commit()

    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )

    # Access page
    response = client.get("/data-register", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK

    # Check for required fields in table
    assert b"Employee records" in response.content
    assert b"Client contact details" in response.content
    assert b"HR database" in response.content
    assert b"Filing cabinet Room 3" in response.content
    assert b"7 years" in response.content
    assert b"5 years" in response.content
    assert b"2026-02-01" in response.content
    assert b"Not reviewed" in response.content

    # Check for IPP reference
    assert b"IPPs 1-4" in response.content or b"IPP" in response.content


def test_data_register_table_structure(client, test_user):
    """Test that data register page has proper table structure."""
    # Login
    response = client.post(
        "/web/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )

    # Access page
    response = client.get("/data-register", follow_redirects=False)
    assert response.status_code == status.HTTP_200_OK

    # Check for table headers
    content = response.content.decode()
    assert "Data Category" in content
    assert "Storage Location" in content
    assert "Retention Period" in content
    assert "Last Reviewed" in content
    assert "Actions" in content or "Edit" in content or "Delete" in content
