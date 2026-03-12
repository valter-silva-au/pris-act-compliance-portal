"""Web routes for serving HTML pages via Jinja2Templates."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.app.auth import (
    SECRET_KEY,
    ALGORITHM,
    authenticate_user,
    get_password_hash,
    create_access_token,
    get_user_by_email,
)
from src.app.database import get_db
from src.app.models import Organization, User

# Create router for web pages
router = APIRouter(tags=["web"])

# Setup Jinja2 templates
templates = Jinja2Templates(directory="src/app/templates")


def get_current_user_from_cookie(request: Request, db: Session) -> User | None:
    """
    Get the current user from the access_token cookie.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User or None: The authenticated user if valid token, None otherwise
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None

        user = get_user_by_email(db, email=email)
        return user
    except JWTError:
        return None


@router.get("/", response_class=RedirectResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    """
    Root endpoint that redirects to dashboard or login based on auth state.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        RedirectResponse: Redirect to /dashboard if authenticated, /web/login otherwise
    """
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)


@router.get("/web/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Display the login page.

    Args:
        request: FastAPI request object

    Returns:
        HTMLResponse: Rendered login page
    """
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/web/login", response_class=RedirectResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle login form submission.

    Args:
        request: FastAPI request object
        username: Email address (form field)
        password: Password (form field)
        db: Database session

    Returns:
        RedirectResponse: Redirect to dashboard on success, or back to login with error
    """
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    # Create response with redirect
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=1800,  # 30 minutes
        samesite="lax"
    )

    return response


@router.get("/web/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Display the registration page.

    Args:
        request: FastAPI request object

    Returns:
        HTMLResponse: Rendered registration page
    """
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/web/register", response_class=RedirectResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(...),
    org_name: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle registration form submission.

    Args:
        request: FastAPI request object
        email: Email address
        full_name: User's full name
        org_name: Organization name
        password: Password
        confirm_password: Password confirmation
        db: Database session

    Returns:
        RedirectResponse: Redirect to login on success, or back to register with error
    """
    # Validate passwords match
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Passwords do not match"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check if user already exists
    existing_user = get_user_by_email(db, email)
    if existing_user:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Email already registered"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Create organization
    import random
    abn = f"{random.randint(10000000000, 99999999999)}"

    org = Organization(name=org_name, abn=abn)
    db.add(org)
    db.flush()

    # Create user
    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role="admin",
        organization_id=org.id
    )
    db.add(user)
    db.commit()

    # Redirect to login page
    return RedirectResponse(url="/web/login", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/auth/logout", response_class=RedirectResponse)
async def logout():
    """
    Handle logout by clearing the access_token cookie.

    Returns:
        RedirectResponse: Redirect to login page
    """
    response = RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Display the dashboard page.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTMLResponse: Rendered dashboard page or redirect to login
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user}
    )
