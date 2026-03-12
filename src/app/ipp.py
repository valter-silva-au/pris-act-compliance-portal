"""IPP Compliance Checklist endpoints for WA PRIS Act Compliance Portal."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from src.app.auth import get_current_user
from src.app.database import get_db
from src.app.models import ComplianceStatus, IPPAssessment, User

# Create router for IPP endpoints
router = APIRouter(tags=["ipp"])

# Setup Jinja2 templates
templates = Jinja2Templates(directory="src/app/templates")

# IPP definitions with names and descriptions
IPP_DEFINITIONS = [
    {
        "number": 1,
        "name": "Collection of personal information",
        "description": "Personal information must be collected lawfully, be necessary for the organization's functions, and collected directly from the individual where reasonable and practical."
    },
    {
        "number": 2,
        "name": "Use and disclosure",
        "description": "Personal information should only be used or disclosed for the purpose for which it was collected, or for a directly related purpose that the individual would reasonably expect."
    },
    {
        "number": 3,
        "name": "Data quality",
        "description": "Organizations must take reasonable steps to ensure personal information is accurate, complete, and up-to-date."
    },
    {
        "number": 4,
        "name": "Data security",
        "description": "Organizations must protect personal information against loss and unauthorized access, use, modification, or disclosure."
    },
    {
        "number": 5,
        "name": "Openness",
        "description": "Organizations must be open about their information handling practices and publish a privacy policy that is publicly available."
    },
    {
        "number": 6,
        "name": "Access to personal information",
        "description": "Individuals have the right to request access to their personal information held by an organization."
    },
    {
        "number": 7,
        "name": "Correction of personal information",
        "description": "Individuals have the right to request correction of their personal information if it is inaccurate, incomplete, or out-of-date."
    },
    {
        "number": 8,
        "name": "Accuracy of personal information before use",
        "description": "Organizations must take reasonable steps to ensure personal information is accurate and up-to-date before using or disclosing it."
    },
    {
        "number": 9,
        "name": "Use of government identifiers",
        "description": "Organizations must not adopt government identifiers (like driver's license numbers) as their own identifier unless authorized."
    },
    {
        "number": 10,
        "name": "Cross-border data transfer restrictions",
        "description": "Organizations must not transfer personal information to recipients outside Western Australia unless certain conditions are met."
    },
    {
        "number": 11,
        "name": "Sensitive information",
        "description": "Sensitive information (health, racial origin, political opinions, etc.) requires additional protections and can only be collected with consent or under specific circumstances."
    }
]


class IPPAssessmentUpdate(BaseModel):
    """Request model for updating IPP assessment."""
    compliance_status: ComplianceStatus
    evidence_notes: str = ""


class IPPAssessmentResponse(BaseModel):
    """Response model for IPP assessment."""
    ipp_number: int
    ipp_name: str
    compliance_status: ComplianceStatus
    evidence_notes: str


def initialize_ipp_assessments(db: Session, organization_id: int):
    """
    Initialize all 11 IPP assessments for an organization if they don't exist.

    Args:
        db: Database session
        organization_id: Organization ID
    """
    for ipp_def in IPP_DEFINITIONS:
        # Check if assessment already exists
        existing = db.query(IPPAssessment).filter(
            IPPAssessment.organization_id == organization_id,
            IPPAssessment.ipp_number == ipp_def["number"]
        ).first()

        if not existing:
            assessment = IPPAssessment(
                ipp_number=ipp_def["number"],
                ipp_name=ipp_def["name"],
                compliance_status=ComplianceStatus.NOT_ASSESSED,
                evidence_notes="",
                organization_id=organization_id
            )
            db.add(assessment)

    db.commit()


def get_compliance_score(assessments: List[IPPAssessment]) -> dict:
    """
    Calculate the overall compliance score.

    Args:
        assessments: List of IPP assessments

    Returns:
        dict: Score information including compliant count and total
    """
    compliant_count = sum(
        1 for a in assessments
        if a.compliance_status == ComplianceStatus.COMPLIANT
    )
    total = len(assessments)

    return {
        "compliant": compliant_count,
        "total": total,
        "percentage": round((compliant_count / total * 100) if total > 0 else 0)
    }


@router.get("/ipp-checklist", response_class=HTMLResponse)
async def get_ipp_checklist(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Display the IPP compliance checklist page.

    Shows all 11 Information Privacy Principles with their compliance status,
    evidence notes, and an overall compliance score.

    Args:
        request: FastAPI request object
        current_user: Authenticated user
        db: Database session

    Returns:
        HTMLResponse: Rendered IPP checklist page
    """
    # Initialize IPP assessments if they don't exist
    initialize_ipp_assessments(db, current_user.organization_id)

    # Get all IPP assessments for the user's organization
    assessments = db.query(IPPAssessment).filter(
        IPPAssessment.organization_id == current_user.organization_id
    ).order_by(IPPAssessment.ipp_number).all()

    # Enrich assessments with descriptions
    for assessment in assessments:
        ipp_def = next(
            (ipp for ipp in IPP_DEFINITIONS if ipp["number"] == assessment.ipp_number),
            None
        )
        if ipp_def:
            assessment.description = ipp_def["description"]

    # Calculate compliance score
    score = get_compliance_score(assessments)

    # Map enum values to display strings
    status_options = [
        {"value": ComplianceStatus.NOT_ASSESSED.value, "label": "Not Assessed"},
        {"value": ComplianceStatus.COMPLIANT.value, "label": "Compliant"},
        {"value": ComplianceStatus.PARTIAL.value, "label": "Partially Compliant"},
        {"value": ComplianceStatus.NON_COMPLIANT.value, "label": "Non-Compliant"}
    ]

    return templates.TemplateResponse(
        "ipp_checklist.html",
        {
            "request": request,
            "assessments": assessments,
            "score": score,
            "status_options": status_options,
            "user": current_user
        }
    )


@router.post("/api/ipp/{ipp_number}", response_class=HTMLResponse)
async def update_ipp_assessment(
    ipp_number: int,
    request: Request,
    assessment_data: IPPAssessmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an IPP assessment and return updated HTML fragment for HTMX.

    Args:
        ipp_number: IPP number (1-11)
        request: FastAPI request object
        assessment_data: Updated assessment data
        current_user: Authenticated user
        db: Database session

    Returns:
        HTMLResponse: Updated compliance score HTML fragment

    Raises:
        HTTPException: If IPP number is invalid or assessment not found
    """
    # Validate IPP number
    if ipp_number < 1 or ipp_number > 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IPP number must be between 1 and 11"
        )

    # Get the assessment
    assessment = db.query(IPPAssessment).filter(
        IPPAssessment.organization_id == current_user.organization_id,
        IPPAssessment.ipp_number == ipp_number
    ).first()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IPP {ipp_number} assessment not found"
        )

    # Update the assessment
    assessment.compliance_status = assessment_data.compliance_status
    assessment.evidence_notes = assessment_data.evidence_notes

    db.commit()
    db.refresh(assessment)

    # Get all assessments to recalculate score
    all_assessments = db.query(IPPAssessment).filter(
        IPPAssessment.organization_id == current_user.organization_id
    ).all()

    # Calculate new compliance score
    score = get_compliance_score(all_assessments)

    # Return updated score HTML fragment for HTMX
    return f"""
    <div id="compliance-score" class="alert alert-info">
        <h4>Overall Compliance Score</h4>
        <p class="mb-0">
            <strong>{score['compliant']}/{score['total']}</strong> IPPs Compliant
            ({score['percentage']}%)
        </p>
    </div>
    """
