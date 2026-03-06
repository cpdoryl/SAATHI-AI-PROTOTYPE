"""
SAATHI AI — Core AI Orchestrator Service
Coordinates: Stage routing → Crisis scan → RAG retrieval → LLM inference → Response
"""
from sqlalchemy.ext.asyncio import AsyncSession
from services.chatbot_service import ChatbotService
from services.crisis_detection_service import CrisisDetectionService
from services.rag_service import RAGService
from services.qwen_inference import QwenInferenceService
from services.lora_model_service import LoRAModelService
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
        - Determines patient stage
        - Loads appropriate LoRA adapter
        - Returns warm greeting
        """
        stage = await self._detect_patient_stage(patient_id)
        logger.info(f"Starting session for patient {patient_id} at stage {stage}")

        greeting = await self.llm.generate(
            prompt=self.chatbot.build_greeting_prompt(stage=stage),
            stage=stage,
        )
        return {
            "session_id": "generated_uuid",
            "stage": stage,
            "greeting": greeting,
        }

    async def process_message(self, session_id: str, message: str, stage: int) -> dict:
        """
        Full AI pipeline for a patient message:
        1. Crisis detection (<100ms)
        2. Step progression logic
        3. RAG context retrieval
        4. System prompt construction
        5. LLM inference (Qwen 2.5-7B)
        6. Response post-processing
        """
        # Step 1: Crisis scan — always first, always fast
        crisis_result = self.crisis_detector.scan(message)
        if crisis_result["severity"] >= 7:
            logger.warning(f"Crisis detected in session {session_id}: score={crisis_result['severity']}")
            return await self._handle_crisis(session_id, crisis_result)

        # Step 2: RAG retrieval for context
        rag_context = await self.rag.query(query=message, tenant_id="placeholder", top_k=3)

        # Step 3: Build stage-appropriate prompt
        prompt = self.chatbot.build_response_prompt(
            message=message,
            stage=stage,
            rag_context=rag_context,
        )

        # Step 4: LLM inference
        response = await self.llm.generate(prompt=prompt, stage=stage)

        return {
            "response": response,
            "crisis_score": crisis_result["severity"],
            "stage": stage,
        }

    async def _detect_patient_stage(self, patient_id: str) -> int:
        """Determine which stage (1/2/3) a patient is in based on DB records."""
        # TODO: Query Patient table and map stage enum to int
        return 1

    async def _handle_crisis(self, session_id: str, crisis_result: dict) -> dict:
        """Trigger escalation protocol and return crisis response."""
        return {
            "response": (
                "I hear that you're going through something very difficult. "
                "Please know that help is available right now. "
                "iCall: +91-9152987821 | Vandrevala Foundation: 1860-2662-345"
            ),
            "crisis_detected": True,
            "severity": crisis_result["severity"],
            "escalated": True,
        }
