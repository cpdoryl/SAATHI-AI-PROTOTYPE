"""
SAATHI AI -- Intent-to-Prompt Mapping
=======================================
Maps IntentClassifierService output to structured prompt instructions
that guide Qwen 2.5-7B's mode, response style, and routing action.

Used by therapeutic_ai_service.py to build intent-aware system prompts.
"""

from typing import Optional

INTENT_PROMPT_TEMPLATES = {
    "seek_support": {
        "mode":           "therapeutic",
        "instruction": (
            "The user is seeking emotional support. "
            "Enter therapeutic listening mode. "
            "Prioritize validation and empathy over advice or information."
        ),
        "response_style": "empathetic, exploratory, non-directive",
        "avoid":          "unsolicited advice, silver linings, minimizing their pain",
    },
    "book_appointment": {
        "mode":           "booking",
        "instruction": (
            "The user wants to schedule a session with a therapist. "
            "Acknowledge their readiness warmly and guide them through "
            "the booking process. Gather their availability."
        ),
        "response_style": "helpful, action-oriented, warm",
        "avoid":          "lengthy therapeutic exploration — focus on scheduling",
    },
    "crisis_emergency": {
        "mode":           "crisis",
        "instruction": (
            "The user has expressed a crisis or emergency intent. "
            "This message must be routed to the crisis protocol immediately. "
            "Do NOT provide generic therapeutic responses. "
            "Acknowledge the seriousness, express care, and connect them to support."
        ),
        "response_style": "calm, direct, present, safety-focused",
        "avoid":          "minimizing, problem-solving, future-focused content",
        "priority":       "HIGHEST -- override all other routing",
    },
    "information_request": {
        "mode":           "educational",
        "instruction": (
            "The user wants factual or educational information. "
            "Retrieve from the knowledge base and present clearly. "
            "After answering, offer follow-up support or a related conversation."
        ),
        "response_style": "clear, educational, supportive",
        "avoid":          "lengthy emotional exploration before answering the question",
    },
    "feedback_complaint": {
        "mode":           "support",
        "instruction": (
            "The user has feedback or a complaint about the platform or service. "
            "Acknowledge sincerely, apologize where appropriate, "
            "and offer a concrete path to resolve the issue."
        ),
        "response_style": "professional, empathetic, solution-oriented",
        "avoid":          "defensiveness, minimizing the complaint",
    },
    "general_chat": {
        "mode":           "conversational",
        "instruction": (
            "The user wants light or casual conversation. "
            "Engage warmly and naturally. "
            "Gently explore what brings them here today without pressure."
        ),
        "response_style": "casual, curious, warm",
        "avoid":          "clinical language, assuming distress, projecting emotions",
    },
    "assessment_request": {
        "mode":           "assessment",
        "instruction": (
            "The user wants to take a clinical assessment. "
            "Ask which assessment they prefer if not specified, "
            "or recommend one based on conversation context "
            "(PHQ-9 for depression, GAD-7 for anxiety, DASS-21 for combined). "
            "Route to the assessment flow."
        ),
        "response_style": "structured, warm, clinical",
        "avoid":          "starting the assessment without confirming which one",
    },
}


def build_intent_context_block(intent_result) -> str:
    """
    Build a structured prompt block from an IntentResult (or dict).
    Returns empty string if intent_result is None.
    """
    if intent_result is None:
        return ""

    # Support both IntentResult dataclass and plain dict
    if hasattr(intent_result, "primary_intent"):
        intent      = intent_result.primary_intent
        confidence  = intent_result.confidence
        routing     = intent_result.routing_action
        secondary   = intent_result.secondary_intent
        sec_conf    = intent_result.secondary_confidence
    else:
        intent      = intent_result.get("primary_intent", "general_chat")
        confidence  = intent_result.get("confidence", 0.5)
        routing     = intent_result.get("routing_action", "CONVERSATIONAL")
        secondary   = intent_result.get("secondary_intent")
        sec_conf    = intent_result.get("secondary_confidence")

    cfg = INTENT_PROMPT_TEMPLATES.get(intent, INTENT_PROMPT_TEMPLATES["general_chat"])

    block = (
        "## User Intent (Intent Classifier)\n"
        f"- Primary Intent  : {intent} (confidence: {confidence:.0%})\n"
        f"- Routing Action  : {routing}\n"
        f"- Mode            : {cfg['mode']}\n"
        f"- Instruction     : {cfg['instruction']}\n"
        f"- Response Style  : {cfg['response_style']}\n"
        f"- Avoid           : {cfg['avoid']}\n"
    )

    if intent == "crisis_emergency":
        block += (
            "\nCRITICAL: Intent Classifier flagged crisis_emergency. "
            "Even if Crisis Detector did not trigger at severity >= 7, "
            "treat this message with elevated care. Do not normalise or redirect away.\n"
        )

    if secondary:
        sec_cfg = INTENT_PROMPT_TEMPLATES.get(secondary, {})
        block += (
            f"\nNote: Secondary intent ({secondary}, "
            f"confidence: {sec_conf:.0%}) also detected.\n"
            f"  Secondary instruction: {sec_cfg.get('instruction', '')}\n"
        )

    return block
