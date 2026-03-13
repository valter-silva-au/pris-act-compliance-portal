"""JWT authentication system for WA PRIS Act Compliance Portal."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.orm import Session

from src.app.database import get_db
from src.app.models import Organization, User, UserRole

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create router for auth endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])


# Pydantic models
class UserRegister(BaseModel):
    """User registration request model."""
    email: EmailStr
    password: str
    full_name: str
    org_name: str


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data model."""
    email: Optional[str] = None


class UserResponse(BaseModel):
    """User response model."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    organization_id: int


class UserInvite(BaseModel):
    """User invitation request model."""
    email: EmailStr
    role: UserRole
    full_name: str


# Password hashing functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to compare against

    Returns:
        bool: True if password matches, False otherwise
    """
    # Truncate password to 72 bytes (bcrypt limit)
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        str: The hashed password
    """
    # Truncate password to 72 bytes (bcrypt limit)
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


# JWT token functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: The data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get a user by email address.

    Args:
        db: Database session
        email: User's email address

    Returns:
        User or None: The user if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.

    Args:
        db: Database session
        email: User's email address
        password: User's plain text password

    Returns:
        User or None: The authenticated user if credentials are valid, None otherwise
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the JWT token.

    Args:
        token: The JWT token from the Authorization header
        db: Database session

    Returns:
        User: The authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


def require_role(allowed_roles: list[UserRole]):
    """
    Create a dependency that requires the user to have one of the specified roles.

    Args:
        allowed_roles: List of roles that are allowed to access the endpoint

    Returns:
        A dependency function that checks the user's role
    """
    async def check_role(current_user: User = Depends(get_current_user)) -> User:
        """Check if the current user has one of the allowed roles."""
        if current_user.role not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join([r.value for r in allowed_roles])}"
            )
        return current_user
    return check_role


# Role-specific dependencies for convenience
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be an admin."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_privacy_officer_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a Privacy Officer or Admin."""
    if current_user.role not in [UserRole.ADMIN.value, UserRole.PRIVACY_OFFICER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privacy Officer or Admin access required"
        )
    return current_user


async def require_any_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be authenticated (any role)."""
    return current_user


# Authentication endpoints
@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user and organization.

    Creates a new organization and user account. The first user of an organization
    is automatically assigned the 'admin' role.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        UserResponse: The created user

    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create organization
    # Generate a simple ABN for demo purposes (in production, this should be provided)
    import random
    abn = f"{random.randint(10000000000, 99999999999)}"

    org = Organization(
        name=user_data.org_name,
        abn=abn
    )
    db.add(org)
    db.flush()  # Flush to get the organization ID

    # Create user with hashed password
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role="admin",  # First user is admin
        organization_id=org.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint that returns a JWT access token.

    Args:
        form_data: OAuth2 password request form with username (email) and password
        db: Database session

    Returns:
        Token: Access token and token type

    Raises:
        HTTPException: If credentials are invalid
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users/invite", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def invite_user(
    invite_data: UserInvite,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Invite a new user to the organization (Admin only).

    Creates a new user account with a temporary password that should be changed on first login.
    Only admins can invite new users.

    Args:
        invite_data: User invitation data (email, role, full_name)
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        UserResponse: The created user

    Raises:
        HTTPException: If email already exists or user is not admin
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, invite_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create a temporary password (in production, this should be sent via email)
    import secrets
    temp_password = secrets.token_urlsafe(16)
    hashed_password = get_password_hash(temp_password)

    # Create user with the specified role
    user = User(
        email=invite_data.email,
        hashed_password=hashed_password,
        full_name=invite_data.full_name,
        role=invite_data.role.value,
        organization_id=current_user.organization_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.get("/users/team", response_model=list[UserResponse])
def get_team_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all users in the current user's organization.

    Returns a list of all team members in the same organization as the current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        list[UserResponse]: List of users in the organization
    """
    users = db.query(User).filter(
        User.organization_id == current_user.organization_id
    ).all()
    return users
