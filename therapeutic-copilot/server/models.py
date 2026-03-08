"""
SAATHI AI — SQLAlchemy ORM Models
All database tables for multi-tenant therapeutic co-pilot platform.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import enum


def gen_uuid():
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class PatientStage(str, enum.Enum):
    LEAD = "lead"
    ACTIVE = "active"
    DROPOUT = "dropout"
    ARCHIVED = "archived"


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CRISIS_ESCALATED = "crisis_escalated"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# ─── Tenant (B2B Clinic/Hospital) ─────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False)
    widget_token = Column(String(255), unique=True, nullable=False)
    plan = Column(String(50), default="basic")           # basic / professional / enterprise
    is_active = Column(Boolean, default=True)
    pinecone_namespace = Column(String(255))              # per-tenant RAG namespace
    razorpay_account_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    clinicians = relationship("Clinician", back_populates="tenant")
    patients = relationship("Patient", back_populates="tenant")


# ─── Clinician ────────────────────────────────────────────────────────────────

class Clinician(Base):
    __tablename__ = "clinicians"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    specialization = Column(String(255))
    google_calendar_token = Column(Text)                 # encrypted OAuth token
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="clinicians")
    patients = relationship("Patient", back_populates="clinician")


# ─── Patient ──────────────────────────────────────────────────────────────────

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    clinician_id = Column(String, ForeignKey("clinicians.id"), nullable=True)
    full_name = Column(String(255))
    phone = Column(String(20))
    email = Column(String(255))
    stage = Column(SAEnum(PatientStage), default=PatientStage.LEAD)
    language = Column(String(10), default="en")
    cultural_context = Column(String(50))
    last_active = Column(DateTime, default=datetime.utcnow)
    dropout_risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="patients")
    clinician = relationship("Clinician", back_populates="patients")
    sessions = relationship("TherapySession", back_populates="patient")
    assessments = relationship("Assessment", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")


# ─── Therapy Session ──────────────────────────────────────────────────────────

class TherapySession(Base):
    __tablename__ = "therapy_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    stage = Column(Integer, default=1)                   # 1, 2, or 3
    current_step = Column(Integer, default=0)            # 0-11 for Stage 2
    status = Column(SAEnum(SessionStatus), default=SessionStatus.PENDING)
    crisis_score = Column(Float, default=0.0)
    session_summary = Column(Text)
    ai_insights = Column(JSON)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)

    patient = relationship("Patient", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session")


# ─── Chat Message ─────────────────────────────────────────────────────────────

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("therapy_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)            # "user" | "assistant"
    content = Column(Text, nullable=False)
    crisis_keywords_detected = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TherapySession", back_populates="messages")


# ─── Assessment ───────────────────────────────────────────────────────────────

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    assessment_type = Column(String(20), nullable=False)  # PHQ-9, GAD-7, etc.
    responses = Column(JSON, nullable=False)
    score = Column(Float)
    severity = Column(String(50))
    administered_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="assessments")


# ─── Appointment ─────────────────────────────────────────────────────────────

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    clinician_id = Column(String, ForeignKey("clinicians.id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    status = Column(SAEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    google_event_id = Column(String(255))
    razorpay_order_id = Column(String(255))
    amount_inr = Column(Float)
    payment_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")


# ─── Audit Log ────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    actor_id = Column(String)                                  # clinician_id or 'system'
    action = Column(String(100))                               # 'login'|'view_patient'|'export_data'
    resource = Column(String(100))                             # 'patient:uuid'|'session:uuid'
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
