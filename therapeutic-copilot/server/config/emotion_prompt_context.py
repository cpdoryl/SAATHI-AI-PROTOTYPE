"""
SAATHI AI -- Emotion-to-Prompt Mapping
=======================================
Maps EmotionClassifierService output to structured prompt instructions
that guide Qwen 2.5-7B's tone, therapeutic technique, and response style.

Used by therapeutic_ai_service.py to build emotion-aware system prompts.
"""

EMOTION_PROMPT_TEMPLATES = {
    "anxiety": {
        "tone":           "calm, grounding, steady",
        "technique":      "breathing exercises, grounding (5-4-3-2-1), cognitive restructuring",
        "avoid":          "catastrophizing language, time pressure, lists of problems",
        "opening_style":  "normalizing and validating",
        "example_opener": (
            "It sounds like you're carrying a lot of worry right now "
            "-- that's completely understandable."
        ),
    },
    "sadness": {
        "tone":           "warm, gentle, present",
        "technique":      "active listening, validation, behavioral activation suggestions",
        "avoid":          "silver linings too quickly, toxic positivity, unsolicited advice",
        "opening_style":  "deep validation before any action",
        "example_opener": (
            "I hear how heavy this feels. "
            "You don't have to have it all figured out right now."
        ),
    },
    "hopelessness": {
        "tone":           "grounding, present, non-directive",
        "technique":      (
            "safety assessment, Socratic questioning about small next steps, "
            "connection, present-moment anchoring"
        ),
        "avoid":          "future-focused plans, comparing to others, statistics",
        "opening_style":  "presence over solution",
        "example_opener": (
            "When everything feels pointless, it's hard to see any way forward. "
            "I'm here with you."
        ),
        "escalation_note": (
            "MONITOR: intensity > 0.80 -> perform safety check before any "
            "other response. Check: 'When you say there's no point -- can you "
            "tell me more about what you mean?'"
        ),
    },
    "anger": {
        "tone":           "non-reactive, validating, curious",
        "technique":      (
            "emotion validation, anger as signal (what need is unmet?), "
            "DBT distress tolerance"
        ),
        "avoid":          "dismissing anger, moralizing, suggesting calming too quickly",
        "opening_style":  "validate before redirecting",
        "example_opener": (
            "That sounds genuinely frustrating. "
            "Your feelings make complete sense given what you've described."
        ),
    },
    "fear": {
        "tone":           "safe, predictable, empowering",
        "technique":      (
            "psychoeducation about fear response, gradual exposure concepts, "
            "safety planning, grounding"
        ),
        "avoid":          "minimizing fear, suggesting it's irrational",
        "opening_style":  "acknowledge the reality of the fear first",
        "example_opener": (
            "That fear sounds very real and very present. "
            "Let's stay with it for a moment."
        ),
    },
    "guilt": {
        "tone":           "compassionate, non-judgmental",
        "technique":      (
            "self-compassion, distinguishing guilt from shame, "
            "reparative action, cognitive reframing"
        ),
        "avoid":          "reassurance too quickly, minimizing",
        "opening_style":  "explore what happened before evaluating",
        "example_opener": (
            "It sounds like you're carrying a heavy weight of responsibility. "
            "Let's understand what happened."
        ),
    },
    "shame": {
        "tone":           "deeply compassionate, slow, careful",
        "technique":      (
            "shame resilience (Brene Brown framework), "
            "connection, normalizing vulnerability"
        ),
        "avoid":          "any hint of judgment, rushing, unsolicited advice",
        "opening_style":  "absolute non-judgment before anything else",
        "example_opener": (
            "What you're describing takes real courage to share. "
            "There's no judgment here."
        ),
    },
    "neutral": {
        "tone":           "engaged, curious, warm",
        "technique":      "open-ended exploration, motivational interviewing",
        "avoid":          "projecting emotions, assuming distress",
        "opening_style":  "curious and open",
        "example_opener": (
            "Thanks for sharing that. "
            "Tell me more about what's been on your mind."
        ),
    },
}


def build_emotion_context_block(emotion_result) -> str:
    """
    Build a structured prompt block from an EmotionResult (or dict).
    Returns empty string if emotion_result is None.
    """
    if emotion_result is None:
        return ""

    if hasattr(emotion_result, "primary_emotion"):
        emotion    = emotion_result.primary_emotion
        intensity  = emotion_result.intensity
        secondary  = emotion_result.secondary_emotion
        high_hope  = emotion_result.high_intensity_hopelessness
    else:
        emotion    = emotion_result.get("primary_emotion", "neutral")
        intensity  = emotion_result.get("intensity", 0.5)
        secondary  = emotion_result.get("secondary_emotion")
        high_hope  = emotion_result.get("high_intensity_hopelessness", False)

    cfg = EMOTION_PROMPT_TEMPLATES.get(emotion,
                                       EMOTION_PROMPT_TEMPLATES["neutral"])

    block = (
        "## Current User Emotional State (Emotion Classifier)\n"
        f"- Primary Emotion  : {emotion} (intensity: {intensity:.0%})\n"
        f"- Secondary Emotion: {secondary if secondary else 'None detected'}\n"
        f"- Recommended Tone : {cfg['tone']}\n"
        f"- Technique        : {cfg['technique']}\n"
        f"- Avoid            : {cfg['avoid']}\n"
        f"- Opening Style    : {cfg['opening_style']}\n"
    )

    if high_hope or (emotion == "hopelessness" and intensity > 0.80):
        block += (
            "\nWARNING -- HIGH INTENSITY HOPELESSNESS DETECTED: "
            "Prioritize safety check and present-moment grounding BEFORE any "
            "other intervention. Ask: 'When you say there's no point -- can you "
            "tell me more about what you mean?'\n"
        )

    if secondary:
        block += (
            f"\nNote: Secondary emotion ({secondary}) also present -- "
            "blend techniques accordingly.\n"
        )

    return block
