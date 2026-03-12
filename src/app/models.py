"""SQLAlchemy ORM models for WA PRIS Act Compliance Portal."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
import enum

from src.app.database import Base


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# Enums for various status and type fields
class PIAStatus(str, enum.Enum):
    """PIA status enum."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RiskLevel(str, enum.Enum):
    """Risk level enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestType(str, enum.Enum):
    """Access request type enum."""
    ACCESS = "access"
    CORRECTION = "correction"


class AccessRequestStatus(str, enum.Enum):
    """Access request status enum."""
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DENIED = "denied"


class BreachIncidentStatus(str, enum.Enum):
    """Breach incident status enum."""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    REPORTED = "reported"


class ComplianceStatus(str, enum.Enum):
    """IPP compliance status enum."""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


class Organization(Base):
    """Organization model."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    abn = Column(String(50), unique=True, nullable=False)
    industry = Column(String(255))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    users = relationship("User", back_populates="organization")
    privacy_officers = relationship("PrivacyOfficer", back_populates="organization")
    pias = relationship("PIA", back_populates="organization")
    data_registers = relationship("DataRegister", back_populates="organization")
    access_requests = relationship("AccessRequest", back_populates="organization")
    breach_incidents = relationship("BreachIncident", back_populates="organization")
    ipp_assessments = relationship("IPPAssessment", back_populates="organization")


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    privacy_officer_profile = relationship("PrivacyOfficer", back_populates="user", uselist=False)
    created_pias = relationship("PIA", back_populates="creator", foreign_keys="PIA.created_by")
    audit_logs = relationship("AuditLog", back_populates="user")


class PrivacyOfficer(Base):
    """Privacy Officer model."""
    __tablename__ = "privacy_officers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    designation_date = Column(Date, nullable=False)
    contact_phone = Column(String(50))

    # Relationships
    user = relationship("User", back_populates="privacy_officer_profile")
    organization = relationship("Organization", back_populates="privacy_officers")


class PIA(Base):
    """Privacy Impact Assessment model."""
    __tablename__ = "pias"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)  # project/initiative description
    data_types = Column(JSON)  # checkboxes: names, addresses, health_info, financial, government_ids, other
    data_flow_description = Column(Text)
    risk_level = Column(Enum(RiskLevel), nullable=False)
    mitigation_measures = Column(Text)
    status = Column(Enum(PIAStatus), nullable=False, default=PIAStatus.DRAFT)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    organization = relationship("Organization", back_populates="pias")
    creator = relationship("User", back_populates="created_pias", foreign_keys=[created_by])


class DataRegister(Base):
    """Data Register model."""
    __tablename__ = "data_registers"

    id = Column(Integer, primary_key=True, index=True)
    data_category = Column(String(255), nullable=False)
    description = Column(Text)
    storage_location = Column(String(255))
    access_controls = Column(Text)
    retention_period = Column(String(255))
    legal_basis = Column(Text)
    date_last_reviewed = Column(Date)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="data_registers")


class AccessRequest(Base):
    """Access Request model."""
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_name = Column(String(255), nullable=False)
    requester_email = Column(String(255), nullable=False)
    request_type = Column(Enum(RequestType), nullable=False)
    description = Column(Text)
    status = Column(Enum(AccessRequestStatus), nullable=False, default=AccessRequestStatus.RECEIVED)
    date_received = Column(DateTime, default=utc_now, nullable=False)
    due_date = Column(Date, nullable=False)
    assigned_handler_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    response_notes = Column(Text)
    date_completed = Column(Date)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    organization = relationship("Organization", back_populates="access_requests")
    assigned_handler = relationship("User", foreign_keys=[assigned_handler_id])


class BreachIncident(Base):
    """Breach Incident model."""
    __tablename__ = "breach_incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    severity = Column(Enum(RiskLevel), nullable=False)
    date_discovered = Column(DateTime, nullable=False)
    date_reported = Column(DateTime)
    affected_records_count = Column(Integer)
    containment_actions = Column(Text)
    status = Column(Enum(BreachIncidentStatus), nullable=False, default=BreachIncidentStatus.DETECTED)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    organization = relationship("Organization", back_populates="breach_incidents")


class IPPAssessment(Base):
    """Information Privacy Principles Assessment model."""
    __tablename__ = "ipp_assessments"

    id = Column(Integer, primary_key=True, index=True)
    ipp_number = Column(Integer, nullable=False)  # 1-11
    ipp_name = Column(String(255), nullable=False)
    compliance_status = Column(Enum(ComplianceStatus), nullable=False, default=ComplianceStatus.NOT_ASSESSED)
    evidence_notes = Column(Text)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    organization = relationship("Organization", back_populates="ipp_assessments")


class AuditLog(Base):
    """Audit Log model."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(Integer)
    details = Column(JSON)
    timestamp = Column(DateTime, default=utc_now, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
