"""Tests for authentication system."""

import pytest
from fastapi import status
from jose import jwt

from src.app.auth import SECRET_KEY, ALGORITHM, get_password_hash, verify_password
from src.app.models import User, Organization


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_password_is_hashed(self):
        """Test that passwords are properly hashed using bcrypt."""
        plain_password = "mysecretpassword123"
        hashed = get_password_hash(plain_password)

        # Verify it's not the plain password
        assert hashed != plain_password
        # Verify it starts with bcrypt identifier
        assert hashed.startswith("$2b$")
        # Verify it can be verified
        assert verify_password(plain_password, hashed)

    def test_password_verify_incorrect(self):
        """Test that incorrect passwords fail verification."""
        plain_password = "mysecretpassword123"
        hashed = get_password_hash(plain_password)

        assert not verify_password("wrongpassword", hashed)

    def test_passwords_never_stored_in_plain_text(self, db, test_user):
        """Test that passwords are never stored in plain text in database."""
        # Get user from database
        user = db.query(User).filter(User.email == test_user.email).first()

        # Verify hashed_password exists
        assert user.hashed_password is not None
        # Verify it's not the plain password
        assert user.hashed_password != "testpassword123"
        # Verify it's a bcrypt hash
        assert user.hashed_password.startswith("$2b$")


class TestRegistration:
    """Test user registration endpoint."""

    def test_register_creates_user_and_org(self, client, db):
        """Test that registration creates both organization and user with 201 status."""
        registration_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User",
            "org_name": "New Organization"
        }

        response = client.post("/auth/register", json=registration_data)

        # Verify 201 Created status
        assert response.status_code == status.HTTP_201_CREATED

        # Verify response data
        data = response.json()
        assert data["email"] == registration_data["email"]
        assert data["full_name"] == registration_data["full_name"]
        assert data["role"] == "admin"  # First user should be admin
        assert "id" in data
        assert "organization_id" in data

        # Verify organization was created in database
        org = db.query(Organization).filter(
            Organization.id == data["organization_id"]
        ).first()
        assert org is not None
        assert org.name == registration_data["org_name"]

        # Verify user was created in database
        user = db.query(User).filter(User.email == registration_data["email"]).first()
        assert user is not None
        assert user.full_name == registration_data["full_name"]
        assert user.role == "admin"

        # Verify password is hashed, not plain text
        assert user.hashed_password != registration_data["password"]
        assert user.hashed_password.startswith("$2b$")
        assert verify_password(registration_data["password"], user.hashed_password)

    def test_register_duplicate_email(self, client, test_user):
        """Test that registering with an existing email returns error."""
        registration_data = {
            "email": test_user.email,  # Using existing email
            "password": "anotherpassword",
            "full_name": "Another User",
            "org_name": "Another Org"
        }

        response = client.post("/auth/register", json=registration_data)

        # Verify 400 Bad Request status
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Test that registration with invalid email fails validation."""
        registration_data = {
            "email": "notanemail",  # Invalid email format
            "password": "securepassword123",
            "full_name": "Test User",
            "org_name": "Test Org"
        }

        response = client.post("/auth/register", json=registration_data)

        # Verify validation error (422 Unprocessable Entity)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLogin:
    """Test login endpoint."""

    def test_login_with_valid_credentials(self, client, test_user):
        """Test that login with valid credentials returns JWT token."""
        login_data = {
            "username": test_user.email,  # OAuth2PasswordRequestForm uses 'username'
            "password": "testpassword123"
        }

        response = client.post("/auth/login", data=login_data)

        # Verify 200 OK status
        assert response.status_code == status.HTTP_200_OK

        # Verify response structure
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

        # Verify token is valid JWT
        token = data["access_token"]
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == test_user.email
        assert "exp" in decoded  # Token has expiration

    def test_login_with_invalid_password(self, client, test_user):
        """Test that login with invalid password returns 401."""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }

        response = client.post("/auth/login", data=login_data)

        # Verify 401 Unauthorized status
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_with_invalid_email(self, client):
        """Test that login with non-existent email returns 401."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "somepassword"
        }

        response = client.post("/auth/login", data=login_data)

        # Verify 401 Unauthorized status
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_returns_bearer_token(self, client, test_user):
        """Test that login returns a bearer token."""
        login_data = {
            "username": test_user.email,
            "password": "testpassword123"
        }

        response = client.post("/auth/login", data=login_data)
        data = response.json()

        assert data["token_type"] == "bearer"


class TestProtectedEndpoints:
    """Test protected endpoints requiring authentication."""

    def test_protected_endpoint_without_token(self, client):
        """Test that accessing protected endpoint without token returns 401."""
        # We'll create a test protected endpoint
        from fastapi import Depends
        from src.app.auth import get_current_user
        from src.app.main import app

        @app.get("/test-protected")
        async def test_protected(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}

        response = client.get("/test-protected")

        # Verify 401 Unauthorized status
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test that accessing protected endpoint with invalid token returns 401."""
        from fastapi import Depends
        from src.app.auth import get_current_user
        from src.app.main import app

        @app.get("/test-protected-invalid")
        async def test_protected_invalid(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}

        # Use an invalid token
        headers = {"Authorization": "Bearer invalid_token_string"}
        response = client.get("/test-protected-invalid", headers=headers)

        # Verify 401 Unauthorized status
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_valid_token(self, client, test_user):
        """Test that accessing protected endpoint with valid token succeeds."""
        from fastapi import Depends
        from src.app.auth import get_current_user
        from src.app.main import app

        @app.get("/test-protected-valid")
        async def test_protected_valid(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}

        # Login to get a valid token
        login_data = {
            "username": test_user.email,
            "password": "testpassword123"
        }
        login_response = client.post("/auth/login", data=login_data)
        token = login_response.json()["access_token"]

        # Access protected endpoint with valid token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/test-protected-valid", headers=headers)

        # Verify 200 OK status
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["user"] == test_user.email


class TestAuthenticationFlow:
    """Test complete authentication flow."""

    def test_complete_register_and_login_flow(self, client, db):
        """Test the complete flow: register -> login -> access protected resource."""
        # Step 1: Register a new user
        registration_data = {
            "email": "flowtest@example.com",
            "password": "flowpassword123",
            "full_name": "Flow Test User",
            "org_name": "Flow Test Org"
        }
        register_response = client.post("/auth/register", json=registration_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        # Step 2: Login with the registered credentials
        login_data = {
            "username": registration_data["email"],
            "password": registration_data["password"]
        }
        login_response = client.post("/auth/login", data=login_data)
        assert login_response.status_code == status.HTTP_200_OK

        token_data = login_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        # Step 3: Verify token contains correct user email
        token = token_data["access_token"]
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == registration_data["email"]

        # Verify password is stored as bcrypt hash in database
        user = db.query(User).filter(User.email == registration_data["email"]).first()
        assert user.hashed_password.startswith("$2b$")
        assert user.hashed_password != registration_data["password"]
