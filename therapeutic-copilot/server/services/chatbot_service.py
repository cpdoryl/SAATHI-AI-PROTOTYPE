"""
SAATHI AI — Chatbot State Machine Service
Manages the 11-step therapeutic flow for Stage 2 conversations.
"""
from typing import Optional


STAGE2_STEPS = [
    "rapport_building",
    "challenge_context",
    "empathetic_connection",
    "challenge_prioritization",
    "exploration_consent",
    "vak_narrative_collection",
    "meta_model_clarification",
    "third_person_perspective",
    "pattern_mapping",
    "feedback_collection",
    "session_summary",
]


class ChatbotService:
    """Manages conversation state and prompt construction for all 3 stages."""

    def build_greeting_prompt(self, stage: int) -> str:
        """Build stage-appropriate system prompt for session opening."""
        if stage == 1:
            return (
                "You are Saathi, a warm and empathetic AI therapeutic co-pilot. "
                "Your goal is to warmly greet the visitor, understand their needs, "
                "and help them book an appointment with a qualified therapist. "
                "Be compassionate, non-judgmental, and culturally sensitive. "
                "Always respond in the language the user prefers."
            )
        elif stage == 2:
            return (
                "You are Saathi, conducting a structured therapeutic co-pilot session. "
                "Follow the 11-step therapeutic framework. Start with Step 1: Rapport Building. "
                "Be empathetic, use open-ended questions, and apply CBT/DBT principles. "
                "Always monitor for crisis indicators."
            )
        else:
            return (
                "You are Saathi, reaching out to a patient who has been inactive. "
                "Your goal is to re-engage them with warmth and without pressure, "
                "and help them reconnect with their therapeutic journey."
            )

    def build_response_prompt(
        self,
        message: str,
        stage: int,
        rag_context: Optional[list] = None,
        current_step: int = 0,
    ) -> str:
        """Build the full system + user prompt for AI inference."""
        system = self.build_greeting_prompt(stage)

        rag_section = ""
        if rag_context:
            rag_section = "\n\nRelevant knowledge base context:\n" + "\n".join(
                [f"- {item}" for item in rag_context]
            )

        step_instruction = ""
        if stage == 2 and current_step < len(STAGE2_STEPS):
            step_name = STAGE2_STEPS[current_step].replace("_", " ").title()
            step_instruction = f"\n\nCurrent therapeutic step: {step_name} (Step {current_step + 1} of 11)"

        return f"{system}{rag_section}{step_instruction}\n\nPatient: {message}\nSaathi:"

    def get_next_step(self, current_step: int) -> int:
        """Advance to the next therapeutic step (capped at 10)."""
        return min(current_step + 1, len(STAGE2_STEPS) - 1)

    def is_session_complete(self, current_step: int) -> bool:
        """Check if all 11 therapeutic steps have been completed."""
        return current_step >= len(STAGE2_STEPS) - 1
