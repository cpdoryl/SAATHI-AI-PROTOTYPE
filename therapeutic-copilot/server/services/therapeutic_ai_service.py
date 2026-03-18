"""
SAATHI AI — Core AI Orchestrator Service
Coordinates: Stage routing → Crisis scan → RAG retrieval → LLM inference → Response
"""
import json
import re
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from services.chatbot_service import ChatbotService
from services.crisis_detection_service import CrisisDetectionService
from services.emotion_classifier_service import get_emotion_service
from services.intent_classifier_service import get_intent_service
from services.topic_classifier_service import get_topic_service
from services.meta_model_detector_service import get_meta_model_detector_service
from services.rag_service import RAGService
from services.qwen_inference import QwenInferenceService
from services.lora_model_service import LoRAModelService
from services.lora_stage1_service import get_stage1_service
from services.lora_stage2_service import (
    get_stage2_service,
    determine_therapeutic_step,
    should_advance_step,
)
from services.websocket_manager import ws_manager
from services.redis_session_service import redis_session_store
from config.emotion_prompt_context import build_emotion_context_block
from config.intent_prompt_context import build_intent_context_block
from config.topic_prompt_context import build_topic_context_block
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

        # Step 2: Emotion + Intent classification (concurrent, ~30ms each)
        import asyncio as _asyncio

        emotion_result        = None
        emotion_context_block = ""
        intent_result         = None
        intent_context_block  = ""
        topic_result          = None
        topic_context_block   = ""
        meta_model_result     = None
        meta_model_block      = ""

        try:
            emo_svc       = get_emotion_service()
            intent_svc    = get_intent_service()
            topic_svc     = get_topic_service()
            meta_model_svc = get_meta_model_detector_service()

            async def _classify_emotion():
                if emo_svc.is_ready:
                    return await _asyncio.get_event_loop().run_in_executor(
                        None, emo_svc.classify, message
                    )
                return None

            async def _classify_intent():
                if intent_svc.is_ready:
                    return await _asyncio.get_event_loop().run_in_executor(
                        None, intent_svc.classify, message
                    )
                return None

            async def _classify_topic():
                if topic_svc.is_ready:
                    return await _asyncio.get_event_loop().run_in_executor(
                        None, topic_svc.classify, message
                    )
                return None

            async def _detect_meta_model():
                # Only run for Stage 2 (therapeutic co-pilot)
                if stage == 2 and meta_model_svc.is_ready:
                    return await _asyncio.get_event_loop().run_in_executor(
                        None, meta_model_svc.detect, message
                    )
                return None

            emo_r, int_r, top_r, meta_r = await _asyncio.gather(
                _classify_emotion(), _classify_intent(),
                _classify_topic(), _detect_meta_model()
            )

            if emo_r:
                emotion_result        = emo_r
                emotion_context_block = build_emotion_context_block(emo_r)
                logger.debug(
                    f"Emotion: {emo_r.primary_emotion} ({emo_r.intensity:.2f}) "
                    f"high_hope={emo_r.high_intensity_hopelessness}"
                )

            if int_r:
                intent_result        = int_r
                intent_context_block = build_intent_context_block(int_r)
                logger.debug(
                    f"Intent: {int_r.primary_intent} ({int_r.confidence:.2f}) "
                    f"routing={int_r.routing_action}"
                )

            if top_r:
                topic_result        = top_r
                topic_context_block = build_topic_context_block(top_r)
                logger.debug(
                    f"Topic: {top_r.primary_topics} multi={top_r.is_multi_label}"
                )

            if meta_r:
                meta_model_result = meta_r
                meta_model_block  = meta_model_svc.build_prompt_context(meta_r)
                logger.debug(
                    f"MetaModel: {meta_r.get('pattern_count', 0)} patterns detected "
                    f"({meta_r.get('processing_time_ms', 0):.0f}ms)"
                )

        except Exception as _exc:
            logger.warning(f"Classifier step skipped: {_exc}")

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
            logger.warning(
                f"Crisis detected in session {session_id}: "
                f"score={crisis_result['severity']}"
            )
            return await self._handle_crisis(
                session_id, crisis_result, session, emotion_result
            )

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
        rag_context = await self.rag.query(
            query=message, tenant_id=tenant_id, top_k=3
        )

        current_step = session.current_step if session else 0
        response = ""
        stage1_result: dict = {}

        if stage == 1:
            # ── Stage 1: Lead Generation via LoRA / Together AI / mock ──────────
            # Load recent chat history for conversation context
            hist_result = await self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at)
                .limit(20)
            )
            history_msgs = hist_result.scalars().all()
            conversation_history = [
                {"role": m.role, "content": m.content} for m in history_msgs
            ]
            # Append the current user message (not yet persisted)
            conversation_history.append({"role": "user", "content": message})

            # Convert classifier results to plain dicts for Stage 1 service
            emo_dict: Optional[dict] = None
            if emotion_result:
                emo_dict = {
                    "primary_emotion": emotion_result.primary_emotion,
                    "intensity": emotion_result.intensity,
                    "secondary_emotion": emotion_result.secondary_emotion,
                }
            top_dict: Optional[dict] = None
            if topic_result:
                primary_topics = topic_result.primary_topics or []
                top_dict = {
                    "primary_topic": primary_topics[0] if primary_topics else None,
                    "all_topics": primary_topics,
                }
            int_dict: Optional[dict] = None
            if intent_result:
                int_dict = {
                    "primary_intent": intent_result.primary_intent,
                    "confidence": intent_result.confidence,
                    "routing_action": intent_result.routing_action,
                }

            stage1_result = await get_stage1_service().generate(
                conversation_history=conversation_history,
                company_name=tenant_id,           # use tenant_id as company name
                turn_number=current_step + 1,     # 1-indexed turn
                emotion_result=emo_dict,
                topic_result=top_dict,
                intent_result=int_dict,
            )
            response = stage1_result.get("response", "")

        elif stage == 2:
            # ── Stage 2: Therapeutic Support via Stage 2 LoRA / Together AI ────
            hist_result = await self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at)
                .limit(30)
            )
            history_msgs = hist_result.scalars().all()
            conversation_history = [
                {"role": m.role, "content": m.content} for m in history_msgs
            ]
            conversation_history.append({"role": "user", "content": message})

            # Build ML context dicts for Stage 2 service
            emo_dict_s2: Optional[dict] = None
            if emotion_result:
                emo_dict_s2 = {
                    "primary_emotion": emotion_result.primary_emotion,
                    "intensity": emotion_result.intensity,
                    "secondary_emotion": emotion_result.secondary_emotion,
                    "high_intensity_hopelessness": (
                        emotion_result.primary_emotion == "hopelessness"
                        and emotion_result.intensity == "high"
                    ),
                }

            meta_dict_s2: Optional[dict] = None
            if meta_model_result:
                meta_dict_s2 = {
                    "patterns_detected": meta_model_result.get("patterns_detected", []),
                }

            top_dict_s2: Optional[dict] = None
            if topic_result:
                primary_topics = topic_result.primary_topics or []
                top_dict_s2 = {
                    "primary_topic": primary_topics[0] if primary_topics else None,
                    "all_topics": primary_topics,
                }

            crisis_ctx_s2: Optional[dict] = {
                "crisis_active": crisis_result["severity"] >= 0.6,
                "severity_score": crisis_result["severity"],
            }

            # Determine presenting issue from topic (best available proxy)
            presenting_issue = "general"
            if top_dict_s2 and top_dict_s2.get("primary_topic"):
                presenting_issue = top_dict_s2["primary_topic"]

            # Determine step name; pass advance hint via current_step + 1 if needed
            therapeutic_step = determine_therapeutic_step(current_step)
            step_for_call = current_step
            if session and should_advance_step(
                therapeutic_step, current_step, emo_dict_s2
            ):
                step_for_call = current_step + 1

            stage2_result = await get_stage2_service().generate(
                conversation_history=conversation_history,
                current_step=step_for_call,
                presenting_issue=presenting_issue,
                session_number=getattr(session, "session_number", 1) if session else 1,
                emotion_result=emo_dict_s2,
                meta_model_result=meta_dict_s2,
                assessment_context=None,   # clinician scores wired separately
                topic_result=top_dict_s2,
                crisis_context=crisis_ctx_s2,
            )
            response = stage2_result.get("response", "")

        else:
            # ── Stage 3: Re-engagement via base Qwen LLM ─────────────────────
            prompt = self.chatbot.build_response_prompt(
                message=message,
                stage=stage,
                rag_context=rag_context,
                current_step=current_step,
            )
            if emotion_context_block:
                prompt = f"{prompt}\n\n{emotion_context_block}"
            if intent_context_block:
                prompt = f"{prompt}\n\n{intent_context_block}"
            if topic_context_block:
                prompt = f"{prompt}\n\n{topic_context_block}"
            if meta_model_block:
                prompt = f"{prompt}\n\n{meta_model_block}"

            response = await self.llm.generate(prompt=prompt, stage=stage)

        # Persist assistant message
        ai_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response,
        )
        self.db.add(ai_msg)

        # Advance step (Stage 1 caps at 8 turns; Stage 2 caps at 10 steps)
        if session:
            if stage == 1 and session.current_step < 8:
                session.current_step += 1
                await redis_session_store.update_step(session_id, session.current_step)
            elif stage == 2 and session.current_step < 10:
                session.current_step += 1
                await redis_session_store.update_step(session_id, session.current_step)
        if session:
            session.crisis_score = max(session.crisis_score or 0.0, crisis_result["severity"])

        await self.db.commit()

        base_response = {
            "response":             response,
            "crisis_score":         crisis_result["severity"],
            "stage":                stage,
            "current_step":         session.current_step if session else 0,
            "ml_crisis_class":      crisis_result.get("ml_crisis_class", "unknown"),
            "ml_model_phase":       crisis_result.get("ml_model_phase", "none"),
            "detection_method":     crisis_result.get("detection_method", "keyword_only"),
            "emotion":              emotion_result.primary_emotion if emotion_result else None,
            "emotion_intensity":    emotion_result.intensity if emotion_result else None,
            "emotion_secondary":    emotion_result.secondary_emotion if emotion_result else None,
            "intent":               intent_result.primary_intent if intent_result else None,
            "intent_confidence":    intent_result.confidence if intent_result else None,
            "routing_action":       intent_result.routing_action if intent_result else None,
            "intent_secondary":     intent_result.secondary_intent if intent_result else None,
            "topics":               topic_result.primary_topics if topic_result else None,
            "topic_multi_label":    topic_result.is_multi_label if topic_result else False,
            "meta_model_patterns":  meta_model_result.get("patterns_detected") if meta_model_result else None,
            "meta_model_count":     meta_model_result.get("pattern_count", 0) if meta_model_result else 0,
        }

        # Stage 1 — enrich response with lead generation signals
        if stage == 1 and stage1_result:
            base_response.update({
                "lead_score":               stage1_result.get("lead_score", 0),
                "lead_factors":             stage1_result.get("lead_factors", {}),
                "booking_intent_detected":  stage1_result.get("booking_intent_detected", False),
                "stage1_backend":           stage1_result.get("backend", "unknown"),
                "stage1_latency_ms":        stage1_result.get("latency_ms", 0),
                "conversation_stage_order": stage1_result.get("stage_order", 1),
            })

        # Stage 2 — enrich response with therapeutic session signals
        elif stage == 2 and stage2_result:
            base_response.update({
                "therapeutic_step":         stage2_result.get("therapeutic_step"),
                "therapeutic_step_number":  stage2_result.get("step_number", current_step),
                "techniques_suggested":     stage2_result.get("techniques_suggested", []),
                "stage2_backend":           stage2_result.get("backend", "unknown"),
                "stage2_latency_ms":        stage2_result.get("latency_ms", 0),
                "safety_check_passed":      stage2_result.get("safety_check_passed", True),
            })

        return base_response

    async def end_session(self, session_id: str) -> dict:
        """
        End a therapy session with AI-generated clinical summary.

        Steps:
        1. Load TherapySession from DB (404 if not found)
        2. Return cached summary if session already COMPLETED
        3. Fetch last 10 messages in chronological order
        4. Build structured summarisation prompt
        5. Call LLM — request JSON {summary, insights}
        6. Parse response; fall back gracefully on JSON parse error
        7. Persist session_summary, ai_insights, status=COMPLETED, ended_at
        8. Delete Redis session cache key
        """
        session_result = await self.db.execute(
            select(TherapySession).where(TherapySession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        # Idempotent: return persisted summary if session already completed
        if session.status == SessionStatus.COMPLETED and session.session_summary:
            logger.info(f"Session {session_id} already completed — returning cached summary")
            return {
                "summary": session.session_summary,
                "insights": session.ai_insights or {},
            }

        # Fetch last 10 messages — DESC limit then reverse for chronological order
        msgs_result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        messages = list(reversed(msgs_result.scalars().all()))

        transcript = "\n".join(
            f"{msg.role.upper()}: {msg.content}" for msg in messages
        )

        summary_prompt = (
            "You are a clinical documentation assistant for a mental health platform. "
            "Analyse the following therapy session transcript and produce a structured summary.\n\n"
            f"SESSION TRANSCRIPT (last {len(messages)} messages):\n"
            f"{transcript}\n\n"
            "Respond with a JSON object containing exactly two keys:\n"
            '  "summary": A 2-4 sentence clinical narrative of the session themes and patient emotional state.\n'
            '  "insights": An object with keys:\n'
            '      "primary_concerns" (list of strings),\n'
            '      "therapeutic_techniques_used" (list of strings),\n'
            '      "patient_engagement" (exactly one of: "high", "medium", or "low"),\n'
            '      "recommended_followup" (string — concrete next step for clinician).\n\n'
            "Respond ONLY with the JSON object. No markdown, no code fences, no extra text."
        )

        raw_response = ""
        try:
            raw_response = await self.llm.generate(
                prompt=summary_prompt,
                stage=session.stage or 1,
                max_tokens=1024,
            )
            logger.debug(f"LLM summary raw response for session {session_id}: {raw_response[:200]}")
        except Exception as exc:
            logger.error(f"LLM summary generation failed for session {session_id}: {exc}")

        # Parse JSON — strip optional markdown code fences before parsing
        summary_text = raw_response.strip()
        ai_insights: dict = {}
        try:
            json_str = summary_text
            # Strip ```json ... ``` or ``` ... ``` wrappers if present
            fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", json_str, re.DOTALL)
            if fence_match:
                json_str = fence_match.group(1)
            parsed = json.loads(json_str)
            summary_text = parsed.get("summary", summary_text)
            ai_insights = parsed.get("insights", {})
        except (json.JSONDecodeError, AttributeError):
            logger.warning(
                f"Could not parse structured JSON from LLM for session {session_id}; "
                "storing raw response as summary"
            )

        # Persist summary, insights, and terminal status to DB
        session.session_summary = summary_text
        session.ai_insights = ai_insights
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.utcnow()
        await self.db.commit()
        logger.info(f"Session {session_id} marked COMPLETED with summary persisted")

        # Remove Redis cache entry — session is no longer active
        await redis_session_store.delete_session(session_id)

        return {
            "summary": summary_text,
            "insights": ai_insights,
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

    async def _handle_crisis(self, session_id: str, crisis_result: dict,
                              session: TherapySession = None,
                              emotion_result=None) -> dict:
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
                "iCall: +91-9152987821 | "
                "Vandrevala Foundation: 1860-2662-345 | "
                "NIMHANS: 080-46110007"
            ),
            "crisis_detected":   True,
            "severity":          crisis_result["severity"],
            "escalated":         True,
            "ml_crisis_class":   crisis_result.get("ml_crisis_class", "unknown"),
            "ml_model_phase":    crisis_result.get("ml_model_phase", "none"),
            "detection_method":  crisis_result.get("detection_method", "keyword_only"),
            "emotion":           emotion_result.primary_emotion if emotion_result else None,
            "emotion_intensity": emotion_result.intensity if emotion_result else None,
        }
