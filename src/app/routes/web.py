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
from src.app.models import (
    Organization, User, PrivacyOfficer, PIA, PIAStatus, RiskLevel, DataRegister,
    AccessRequest, RequestType, AccessRequestStatus
)
from datetime import date, timedelta
import json

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


@router.get("/privacy-officer", response_class=HTMLResponse)
async def privacy_officer_page(request: Request, db: Session = Depends(get_db)):
    """
    Display the Privacy Officer page.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTMLResponse: Rendered privacy officer page or redirect to login
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Get current privacy officer for the organization
    officer = db.query(PrivacyOfficer).filter(
        PrivacyOfficer.organization_id == user.organization_id
    ).first()

    # Get all users in the organization for the dropdown
    org_users = db.query(User).filter(
        User.organization_id == user.organization_id
    ).all()

    return templates.TemplateResponse(
        "privacy_officer.html",
        {
            "request": request,
            "user": user,
            "officer": officer,
            "org_users": org_users
        }
    )


@router.post("/api/privacy-officer", response_class=HTMLResponse)
async def designate_privacy_officer(
    request: Request,
    user_id: int = Form(...),
    contact_phone: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Designate or update the Privacy Officer.

    Args:
        request: FastAPI request object
        user_id: ID of the user to designate as privacy officer
        contact_phone: Optional contact phone number
        db: Database session

    Returns:
        HTMLResponse: Redirect to privacy officer page or error
    """
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can designate privacy officers"
        )

    # Verify the selected user exists and belongs to the same organization
    selected_user = db.query(User).filter(User.id == user_id).first()
    if not selected_user:
        # Get org users for re-rendering
        org_users = db.query(User).filter(
            User.organization_id == current_user.organization_id
        ).all()
        officer = db.query(PrivacyOfficer).filter(
            PrivacyOfficer.organization_id == current_user.organization_id
        ).first()
        return templates.TemplateResponse(
            "privacy_officer.html",
            {
                "request": request,
                "user": current_user,
                "officer": officer,
                "org_users": org_users,
                "error": "Selected user not found"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if selected_user.organization_id != current_user.organization_id:
        # Get org users for re-rendering
        org_users = db.query(User).filter(
            User.organization_id == current_user.organization_id
        ).all()
        officer = db.query(PrivacyOfficer).filter(
            PrivacyOfficer.organization_id == current_user.organization_id
        ).first()
        return templates.TemplateResponse(
            "privacy_officer.html",
            {
                "request": request,
                "user": current_user,
                "officer": officer,
                "org_users": org_users,
                "error": "Selected user does not belong to your organization"
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Check if there's an existing privacy officer
    existing_officer = db.query(PrivacyOfficer).filter(
        PrivacyOfficer.organization_id == current_user.organization_id
    ).first()

    if existing_officer:
        # Update existing officer
        existing_officer.user_id = user_id
        existing_officer.designation_date = date.today()
        existing_officer.contact_phone = contact_phone
    else:
        # Create new privacy officer
        new_officer = PrivacyOfficer(
            user_id=user_id,
            organization_id=current_user.organization_id,
            designation_date=date.today(),
            contact_phone=contact_phone
        )
        db.add(new_officer)

    db.commit()

    # Redirect back to the privacy officer page
    return RedirectResponse(url="/privacy-officer", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/pias", response_class=HTMLResponse)
async def pias_list(request: Request, db: Session = Depends(get_db)):
    """
    Display list of all PIAs.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTMLResponse: Rendered PIAs list page or redirect to login
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Get all PIAs for the organization
    pias = db.query(PIA).filter(
        PIA.organization_id == user.organization_id
    ).order_by(PIA.created_at.desc()).all()

    return templates.TemplateResponse(
        "pias_list.html",
        {
            "request": request,
            "user": user,
            "pias": pias
        }
    )


@router.get("/pias/new", response_class=HTMLResponse)
async def pias_new(request: Request, db: Session = Depends(get_db)):
    """
    Display PIA creation form.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTMLResponse: Rendered PIA creation form or redirect to login
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "pias_new.html",
        {
            "request": request,
            "user": user
        }
    )


@router.get("/pias/{pia_id}", response_class=HTMLResponse)
async def pias_detail(request: Request, pia_id: int, db: Session = Depends(get_db)):
    """
    Display PIA detail page with edit capability.

    Args:
        request: FastAPI request object
        pia_id: PIA ID
        db: Database session

    Returns:
        HTMLResponse: Rendered PIA detail page or redirect to login
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Get the PIA
    pia = db.query(PIA).filter(
        PIA.id == pia_id,
        PIA.organization_id == user.organization_id
    ).first()

    if not pia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PIA not found"
        )

    return templates.TemplateResponse(
        "pias_detail.html",
        {
            "request": request,
            "user": user,
            "pia": pia
        }
    )


@router.post("/api/pias", response_class=RedirectResponse)
async def create_pia(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    data_types_names: bool = Form(False),
    data_types_addresses: bool = Form(False),
    data_types_health: bool = Form(False),
    data_types_financial: bool = Form(False),
    data_types_gov_ids: bool = Form(False),
    data_types_other: bool = Form(False),
    data_flow_description: str = Form(...),
    risk_level: str = Form(...),
    mitigation_measures: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Create a new PIA in draft status.

    Args:
        request: FastAPI request object
        title: PIA title
        description: Project/initiative description
        data_types_*: Checkboxes for data types involved
        data_flow_description: Description of data flow
        risk_level: Risk level assessment
        mitigation_measures: Mitigation measures
        db: Database session

    Returns:
        RedirectResponse: Redirect to PIAs list page
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Build data_types JSON
    data_types = {
        "names": data_types_names,
        "addresses": data_types_addresses,
        "health_info": data_types_health,
        "financial": data_types_financial,
        "government_ids": data_types_gov_ids,
        "other": data_types_other
    }

    # Create new PIA
    new_pia = PIA(
        title=title,
        description=description,
        data_types=data_types,
        data_flow_description=data_flow_description,
        risk_level=RiskLevel(risk_level),
        mitigation_measures=mitigation_measures,
        status=PIAStatus.DRAFT,
        organization_id=user.organization_id,
        created_by=user.id
    )
    db.add(new_pia)
    db.commit()

    # Redirect to PIAs list
    return RedirectResponse(url="/pias", status_code=status.HTTP_303_SEE_OTHER)


@router.put("/api/pias/{pia_id}", response_class=RedirectResponse)
@router.post("/api/pias/{pia_id}", response_class=RedirectResponse)  # HTML forms only support POST
async def update_pia(
    request: Request,
    pia_id: int,
    title: str = Form(...),
    description: str = Form(...),
    data_types_names: bool = Form(False),
    data_types_addresses: bool = Form(False),
    data_types_health: bool = Form(False),
    data_types_financial: bool = Form(False),
    data_types_gov_ids: bool = Form(False),
    data_types_other: bool = Form(False),
    data_flow_description: str = Form(...),
    risk_level: str = Form(...),
    mitigation_measures: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Update PIA fields.

    Args:
        request: FastAPI request object
        pia_id: PIA ID
        title: PIA title
        description: Project/initiative description
        data_types_*: Checkboxes for data types involved
        data_flow_description: Description of data flow
        risk_level: Risk level assessment
        mitigation_measures: Mitigation measures
        db: Database session

    Returns:
        RedirectResponse: Redirect to PIA detail page
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Get the PIA
    pia = db.query(PIA).filter(
        PIA.id == pia_id,
        PIA.organization_id == user.organization_id
    ).first()

    if not pia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PIA not found"
        )

    # Build data_types JSON
    data_types = {
        "names": data_types_names,
        "addresses": data_types_addresses,
        "health_info": data_types_health,
        "financial": data_types_financial,
        "government_ids": data_types_gov_ids,
        "other": data_types_other
    }

    # Update PIA fields
    pia.title = title
    pia.description = description
    pia.data_types = data_types
    pia.data_flow_description = data_flow_description
    pia.risk_level = RiskLevel(risk_level)
    pia.mitigation_measures = mitigation_measures

    db.commit()

    # Redirect to PIA detail page
    return RedirectResponse(url=f"/pias/{pia_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.patch("/api/pias/{pia_id}/status")
async def update_pia_status(
    request: Request,
    pia_id: int,
    status_value: str = Form(..., alias="status"),
    db: Session = Depends(get_db)
):
    """
    Transition PIA status via HTMX.

    Args:
        request: FastAPI request object
        pia_id: PIA ID
        status_value: New status value
        db: Database session

    Returns:
        dict: Updated PIA status information for HTMX response
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Get the PIA
    pia = db.query(PIA).filter(
        PIA.id == pia_id,
        PIA.organization_id == user.organization_id
    ).first()

    if not pia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PIA not found"
        )

    # Update status
    pia.status = PIAStatus(status_value)
    db.commit()

    # Return the updated status HTML fragment
    status_badges = {
        "draft": "bg-gray-100 text-gray-800",
        "in_review": "bg-blue-100 text-blue-800",
        "approved": "bg-green-100 text-green-800",
        "rejected": "bg-red-100 text-red-800"
    }
    badge_class = status_badges.get(pia.status.value, "bg-gray-100 text-gray-800")

    return {
        "status": pia.status.value,
        "badge_html": f'<span class="px-2 py-1 text-xs font-semibold rounded-full {badge_class}">{pia.status.value.replace("_", " ").title()}</span>'
    }


@router.get("/data-register", response_class=HTMLResponse)
async def data_register_page(request: Request, db: Session = Depends(get_db)):
    """
    Display the Data Register page showing all personal information holdings.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTMLResponse: Rendered data register page or redirect to login
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Get all data register entries for the organization
    data_entries = db.query(DataRegister).filter(
        DataRegister.organization_id == user.organization_id
    ).order_by(DataRegister.data_category).all()

    return templates.TemplateResponse(
        "data_register.html",
        {
            "request": request,
            "user": user,
            "data_entries": data_entries
        }
    )


@router.post("/api/data-register", response_class=RedirectResponse)
async def create_data_register_entry(
    request: Request,
    data_category: str = Form(...),
    description: str = Form(""),
    storage_location: str = Form(""),
    access_controls: str = Form(""),
    retention_period: str = Form(""),
    legal_basis: str = Form(""),
    date_last_reviewed: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Create a new data register entry.

    Args:
        request: FastAPI request object
        data_category: Category of personal information
        description: Description of the data
        storage_location: Where the data is stored
        access_controls: Who can access the data
        retention_period: How long data is retained
        legal_basis: Legal basis for collecting the data
        date_last_reviewed: Date the entry was last reviewed
        db: Database session

    Returns:
        RedirectResponse: Redirect to data register page
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Parse date if provided
    parsed_date = None
    if date_last_reviewed:
        try:
            from datetime import datetime
            parsed_date = datetime.strptime(date_last_reviewed, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Create new data register entry
    new_entry = DataRegister(
        data_category=data_category,
        description=description if description else None,
        storage_location=storage_location if storage_location else None,
        access_controls=access_controls if access_controls else None,
        retention_period=retention_period if retention_period else None,
        legal_basis=legal_basis if legal_basis else None,
        date_last_reviewed=parsed_date,
        organization_id=user.organization_id
    )
    db.add(new_entry)
    db.commit()

    return RedirectResponse(url="/data-register", status_code=status.HTTP_303_SEE_OTHER)


@router.put("/api/data-register/{entry_id}", response_class=RedirectResponse)
@router.post("/api/data-register/{entry_id}", response_class=RedirectResponse)
async def update_data_register_entry(
    request: Request,
    entry_id: int,
    data_category: str = Form(...),
    description: str = Form(""),
    storage_location: str = Form(""),
    access_controls: str = Form(""),
    retention_period: str = Form(""),
    legal_basis: str = Form(""),
    date_last_reviewed: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Update an existing data register entry.

    Args:
        request: FastAPI request object
        entry_id: ID of the entry to update
        data_category: Category of personal information
        description: Description of the data
        storage_location: Where the data is stored
        access_controls: Who can access the data
        retention_period: How long data is retained
        legal_basis: Legal basis for collecting the data
        date_last_reviewed: Date the entry was last reviewed
        db: Database session

    Returns:
        RedirectResponse: Redirect to data register page
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Get the data register entry
    entry = db.query(DataRegister).filter(
        DataRegister.id == entry_id,
        DataRegister.organization_id == user.organization_id
    ).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data register entry not found"
        )

    # Parse date if provided
    parsed_date = None
    if date_last_reviewed:
        try:
            from datetime import datetime
            parsed_date = datetime.strptime(date_last_reviewed, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Update entry
    entry.data_category = data_category
    entry.description = description if description else None
    entry.storage_location = storage_location if storage_location else None
    entry.access_controls = access_controls if access_controls else None
    entry.retention_period = retention_period if retention_period else None
    entry.legal_basis = legal_basis if legal_basis else None
    entry.date_last_reviewed = parsed_date

    db.commit()

    return RedirectResponse(url="/data-register", status_code=status.HTTP_303_SEE_OTHER)


@router.delete("/api/data-register/{entry_id}")
async def delete_data_register_entry(
    request: Request,
    entry_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a data register entry.

    Args:
        request: FastAPI request object
        entry_id: ID of the entry to delete
        db: Database session

    Returns:
        dict: Success message
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Get the data register entry
    entry = db.query(DataRegister).filter(
        DataRegister.id == entry_id,
        DataRegister.organization_id == user.organization_id
    ).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data register entry not found"
        )

    db.delete(entry)
    db.commit()

    return {"message": "Data register entry deleted successfully"}


@router.get("/requests", response_class=HTMLResponse)
async def requests_list(request: Request, db: Session = Depends(get_db)):
    """
    Display list of all access and correction requests.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTMLResponse: Rendered requests list page or redirect to login
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Get all requests for the organization
    requests = db.query(AccessRequest).filter(
        AccessRequest.organization_id == user.organization_id
    ).order_by(AccessRequest.created_at.desc()).all()

    # Get all users in the organization for the handler dropdown
    org_users = db.query(User).filter(
        User.organization_id == user.organization_id
    ).all()

    return templates.TemplateResponse(
        "requests.html",
        {
            "request": request,
            "user": user,
            "requests": requests,
            "org_users": org_users
        }
    )


@router.post("/api/requests", response_class=RedirectResponse)
async def create_request(
    request: Request,
    requester_name: str = Form(...),
    requester_email: str = Form(...),
    request_type: str = Form(...),
    description: str = Form(""),
    assigned_handler_id: int = Form(None),
    db: Session = Depends(get_db)
):
    """
    Create a new access or correction request with auto-calculated due date.

    Args:
        request: FastAPI request object
        requester_name: Name of the requester
        requester_email: Email of the requester
        request_type: Type of request (access or correction)
        description: Description of what's requested
        assigned_handler_id: Optional user ID to assign the request to
        db: Database session

    Returns:
        RedirectResponse: Redirect to requests list page
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Calculate due date: 45 days from today (PRIS Act requirement)
    due_date = date.today() + timedelta(days=45)

    # Create new request
    new_request = AccessRequest(
        requester_name=requester_name,
        requester_email=requester_email,
        request_type=RequestType(request_type),
        description=description if description else None,
        status=AccessRequestStatus.RECEIVED,
        due_date=due_date,
        assigned_handler_id=assigned_handler_id if assigned_handler_id else None,
        organization_id=user.organization_id
    )
    db.add(new_request)
    db.commit()

    return RedirectResponse(url="/requests", status_code=status.HTTP_303_SEE_OTHER)


@router.put("/api/requests/{request_id}", response_class=RedirectResponse)
@router.post("/api/requests/{request_id}", response_class=RedirectResponse)
async def update_request(
    request: Request,
    request_id: int,
    requester_name: str = Form(...),
    requester_email: str = Form(...),
    request_type: str = Form(...),
    description: str = Form(""),
    assigned_handler_id: int = Form(None),
    status_value: str = Form(..., alias="status"),
    response_notes: str = Form(""),
    date_completed: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Update an access or correction request.

    Args:
        request: FastAPI request object
        request_id: Request ID
        requester_name: Name of the requester
        requester_email: Email of the requester
        request_type: Type of request (access or correction)
        description: Description of what's requested
        assigned_handler_id: Optional user ID to assign the request to
        status_value: Request status
        response_notes: Notes about the response
        date_completed: Date the request was completed
        db: Database session

    Returns:
        RedirectResponse: Redirect to requests list page
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    # Get the request
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.organization_id == user.organization_id
    ).first()

    if not access_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )

    # Parse date_completed if provided
    parsed_date_completed = None
    if date_completed:
        try:
            from datetime import datetime
            parsed_date_completed = datetime.strptime(date_completed, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Update request fields
    access_request.requester_name = requester_name
    access_request.requester_email = requester_email
    access_request.request_type = RequestType(request_type)
    access_request.description = description if description else None
    access_request.assigned_handler_id = assigned_handler_id if assigned_handler_id else None
    access_request.status = AccessRequestStatus(status_value)
    access_request.response_notes = response_notes if response_notes else None
    access_request.date_completed = parsed_date_completed

    db.commit()

    return RedirectResponse(url="/requests", status_code=status.HTTP_303_SEE_OTHER)
