"""Pydantic v2 request/response schemas for Saathi AI API."""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Chat ─────────────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    patient_id: Optional[str] = None
    tenant_id: str
    widget_token: str
    language: str = "en"


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str
    stage: int = 1


class ChatResponse(BaseModel):
    response: str
    session_id: str
    crisis_score: float = 0.0
    escalated: bool = False


# ─── Assessment ───────────────────────────────────────────────────────────────

class AssessmentSubmitRequest(BaseModel):
    assessment_type: str
    responses: List[int]


class AssessmentResult(BaseModel):
    assessment_type: str
    total_score: int
    severity: str
    max_possible: int


# ─── Appointment ─────────────────────────────────────────────────────────────

class AppointmentCreateRequest(BaseModel):
    patient_id: str
    clinician_id: str
    scheduled_at: datetime
    duration_minutes: int = 60
    amount_inr: float


# ─── Payment ─────────────────────────────────────────────────────────────────

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ─── Tenant ───────────────────────────────────────────────────────────────────

class TenantCreateRequest(BaseModel):
    name: str
    domain: str
    plan: str = "basic"
