"""
SAATHI AI — SQLAlchemy ORM Models
Re-exported here because the models/ package takes precedence over models.py.
All model definitions live in models.py; this file re-exports them.
"""
import importlib.util
import os
import sys

# Load models.py explicitly (this file's package shadows it otherwise)
_models_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models.py")
_spec = importlib.util.spec_from_file_location("_saathi_orm_models", _models_py_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_saathi_orm_models"] = _mod
_spec.loader.exec_module(_mod)

# Re-export all public ORM names so `from models import Clinician` works
from _saathi_orm_models import (  # noqa: F401
    Base,
    gen_uuid,
    PatientStage,
    SessionStatus,
    AppointmentStatus,
    Tenant,
    Clinician,
    Patient,
    TherapySession,
    ChatMessage,
    Assessment,
    Appointment,
)
