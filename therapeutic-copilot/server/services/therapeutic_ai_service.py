"""
SAATHI AI — Core AI Orchestrator Service
Coordinates: Stage routing → Crisis scan → RAG retrieval → LLM inference → Response
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from services.chatbot_service import ChatbotService
from services.crisis_detection_service import CrisisDetectionService
from services.rag_service import RAGService
from services.qwen_inference import QwenInferenceService
from services.lora_model_service import LoRAModelService
from services.websocket_manager import ws_manager
from services.redis_session_service import redis_session_store
from models import Patient, PatientStage, TherapySession, SessionStatus, ChatMessage
from loguru import logger


class TherapeuticAIService:
    """
    Main orchestrator for the 3-stage therapeutic conversation pipeline.

    Stage 1 — Lead generation (LoRA adapter r=8, 634 examples)
    Stage 2 — Therapeutic co-pilot (LoRA adapter r=16, 3,017 examples)
    Stage 3 — Dropout re-engagement
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.chatbot = ChatbotService()
        self.crisis_detector = CrisisDetectionService()
        self.rag = RAGService()
        self.llm = QwenInferenceService()
        self.lora = LoRAModelService()

    async def start_session(self, patient_id: str, tenant_id: str, widget_token: str) -> dict:
        """
        Initialise a new therapy session.
        - Determines patient stage from DB
        - Creates TherapySession record
        - Returns warm greeting
        """
        stage = await self._detect_patient_stage(patient_id)
        logger.info(f"Starting session for patient {patient_id} at stage {stage}")

        session = TherapySession(
            patient_id=patient_id,
            stage=stage,
            current_step=0,
            status=SessionStatus.IN_PROGRESS,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        # Cache session state in Redis for fast subsequent lookups
        await redis_session_store.set_session(session.id, {
            "patient_id": patient_id,
            "tenant_id": tenant_id or "default",
            "stage": stage,
            "current_step": 0,
            "status": SessionStatus.IN_PROGRESS.value,
        })

        greeting = await self.llm.generate(
            prompt=self.chatbot.build_greeting_prompt(stage=stage),
            stage=stage,
        )
        return {
            "session_id": session.id,
            "stage": stage,
            "greeting": greeting,
        }

    async def process_message(self, session_id: str, message: str, stage: int) -> dict:
        """
        Full AI pipeline for a patient message:
        1. Load session from DB
        2. Crisis detection (<100ms)
        3. Persist user ChatMessage
        4. RAG context retrieval (tenant-scoped)
        5. System prompt construction with current step
        6. LLM inference (Qwen 2.5-7B)
        7. Persist assistant ChatMessage
        8. Advance Stage 2 step
        """
        # Try Redis cache first; fall back to DB if cache miss
        cached = await redis_session_store.get_session(session_id)
        if cached:
            await redis_session_store.refresh_ttl(session_id)

        result = await self.db.execute(
            select(TherapySession).where(TherapySession.id == session_id)
        )
        session = result.scalar_one_or_none()

        # Step 1: Crisis scan — always first, always fast
        crisis_result = self.crisis_detector.scan(message)

        # Persist user message (with any detected crisis keywords)
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=message,
            crisis_keywords_detected=crisis_result.get("detected_keywords", []),
        )
        self.db.add(user_msg)

        if crisis_result["severity"] >= 7:
            if session:
                session.status = SessionStatus.CRISIS_ESCALATED
                session.crisis_score = crisis_result["severity"]
            await self.db.commit()
            logger.warning(f"Crisis detected in session {session_id}: score={crisis_result['severity']}")
            return await self._handle_crisis(session_id, crisis_result, session)

        # Resolve tenant_id for RAG (fall back to "default" if session not found)
        tenant_id = "default"
        if session:
            patient_result = await self.db.execute(
                select(Patient).where(Patient.id == session.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient and patient.tenant_id:
                tenant_id = patient.tenant_id

        # RAG retrieval for tenant-specific context
        rag_context = await self.rag.query(query=message, tenant_id=tenant_id, top_k=3)

        # Build prompt using current step position
        current_step = session.current_step if session else 0
        prompt = self.chatbot.build_response_prompt(
            message=message,
            stage=stage,
            rag_context=rag_context,
            current_step=current_step,
        )

        # LLM inference
        response = await self.llm.generate(prompt=prompt, stage=stage)

        # Persist assistant message
        ai_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response,
        )
        self.db.add(ai_msg)

        # Advance step for Stage 2 (caps at step 10, the final step)
        if session and stage == 2 and session.current_step < 10:
            session.current_step += 1
            # Sync updated step back to Redis cache
            await redis_session_store.update_step(session_id, session.current_step)
        if session:
            session.crisis_score = max(session.crisis_score or 0.0, crisis_result["severity"])

        await self.db.commit()

        return {
            "response": response,
            "crisis_score": crisis_result["severity"],
            "stage": stage,
            "current_step": session.current_step if session else 0,
        }

    async def _detect_patient_stage(self, patient_id: str) -> int:
        """Determine which stage (1/2/3) a patient is in based on DB records."""
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            return 1  # new/unknown patient defaults to lead stage

        stage_map = {
            PatientStage.LEAD: 1,
            PatientStage.ACTIVE: 2,
            PatientStage.DROPOUT: 3,
            PatientStage.ARCHIVED: 1,
        }
        return stage_map.get(patient.stage, 1)

    async def _handle_crisis(self, session_id: str, crisis_result: dict, session: TherapySession = None) -> dict:
        """
        Trigger escalation protocol:
        - Broadcast WebSocket alert to clinician dashboard
        - Return emergency resource response to patient
        """
        # Send real-time alert to the assigned clinician's dashboard
        if session:
            patient_result = await self.db.execute(
                select(Patient).where(Patient.id == session.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient and patient.clinician_id:
                await ws_manager.send_crisis_alert(
                    clinician_id=patient.clinician_id,
                    alert_data={
                        "session_id": session_id,
                        "patient_id": session.patient_id,
                        "severity": crisis_result["severity"],
                        "keywords": crisis_result.get("detected_keywords", []),
                    },
                )
                logger.info(f"Crisis alert sent to clinician {patient.clinician_id}")

        return {
            "response": (
                "I hear that you're going through something very difficult. "
                "Please know that help is available right now.\n\n"
                "iCall: +91-9152987821 | Vandrevala Foundation: 1860-2662-345 | NIMHANS: 080-46110007"
            ),
            "crisis_detected": True,
            "severity": crisis_result["severity"],
            "escalated": True,
        }
