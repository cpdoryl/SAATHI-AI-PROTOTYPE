"""
SAATHI AI -- Topic-to-Prompt Mapping
=======================================
Maps TopicClassifierService output to structured prompt instructions
that guide Qwen 2.5-7B's contextual focus based on detected life domain(s).

Supports multi-label: when 2 topics co-occur, both context blocks are surfaced.
Used by therapeutic_ai_service.py to build topic-aware system prompts.
"""

from typing import Optional

TOPIC_PROMPT_TEMPLATES = {
    "workplace_stress": {
        "domain":      "Work & Career",
        "instruction": (
            "The user is experiencing workplace or career-related stress. "
            "Acknowledge the professional context — pressures like workload, "
            "manager conflict, job insecurity, or burnout. "
            "Validate that work stress is real and serious. "
            "Explore what specific aspect is weighing on them most."
        ),
        "key_themes":  "burnout, toxic workplace, job loss fears, performance pressure, work-life imbalance",
        "helpful_prompts": (
            "What is it about work that feels most overwhelming right now? "
            "How long have you been feeling this way?"
        ),
    },
    "relationship_issues": {
        "domain":      "Relationships & Family",
        "instruction": (
            "The user is dealing with relationship difficulties — romantic, family, "
            "friendships, or social isolation. "
            "Create safety for vulnerability. Avoid taking sides or judging. "
            "Explore the relational pain with curiosity and care."
        ),
        "key_themes":  "conflict, breakup, loneliness, family tension, trust issues, social isolation",
        "helpful_prompts": (
            "What is the relationship like when it's good? "
            "What feels most hurtful right now?"
        ),
    },
    "academic_stress": {
        "domain":      "Academic & Educational Stress",
        "instruction": (
            "The user is under academic pressure — exams, performance anxiety, "
            "fear of failure, or feeling overwhelmed by their course load. "
            "Normalise academic stress while exploring the deeper fears underneath "
            "(failure, parental expectations, identity). "
            "Avoid giving study tips unless asked."
        ),
        "key_themes":  "exam anxiety, failure fear, parental pressure, academic identity, performance anxiety",
        "helpful_prompts": (
            "What does failing feel like it would mean for you? "
            "Is there anyone you feel you can talk to about this pressure?"
        ),
    },
    "health_concerns": {
        "domain":      "Health & Medical Wellbeing",
        "instruction": (
            "The user has health-related concerns — chronic illness, medical diagnosis, "
            "body image, physical symptoms, or health anxiety. "
            "Validate the fear and uncertainty that health concerns carry. "
            "Do NOT provide medical advice. "
            "Explore their emotional experience of the health concern."
        ),
        "key_themes":  "illness, diagnosis, medical anxiety, chronic pain, body image, health uncertainty",
        "helpful_prompts": (
            "How has this health concern been affecting your day-to-day life? "
            "Do you have support from people around you?"
        ),
        "caution": "NEVER diagnose or recommend medical treatment. Refer to healthcare professionals.",
    },
    "financial_stress": {
        "domain":      "Financial Stress & Economic Pressure",
        "instruction": (
            "The user is experiencing financial stress — debt, poverty, income insecurity, "
            "or financial shame. "
            "Acknowledge that money stress often carries shame and isolation. "
            "Normalise the emotional weight of financial difficulty without minimising it. "
            "Explore how it is affecting their sense of safety and self-worth."
        ),
        "key_themes":  "debt, poverty, income loss, financial shame, economic anxiety, survival stress",
        "helpful_prompts": (
            "How is this financial pressure affecting how you feel about yourself? "
            "Is there anyone in your life you can lean on right now?"
        ),
    },
}


def build_topic_context_block(topic_result) -> str:
    """
    Build a structured prompt block from a TopicResult (or dict).
    Handles multi-label: surfaces context for all detected topics.
    Returns empty string if topic_result is None.
    """
    if topic_result is None:
        return ""

    # Support both TopicResult dataclass and plain dict
    if hasattr(topic_result, "primary_topics"):
        topics       = topic_result.primary_topics
        all_scores   = topic_result.all_scores
        is_multi     = topic_result.is_multi_label
    else:
        topics       = topic_result.get("primary_topics", [])
        all_scores   = topic_result.get("all_scores", {})
        is_multi     = topic_result.get("is_multi_label", False)

    if not topics:
        return ""

    lines = ["## Conversation Topic (Topic Classifier)"]

    if is_multi:
        lines.append(f"- Co-occurring topics detected: {', '.join(topics)}")
        lines.append(
            "- Note: User's concern spans multiple life domains — address both with care."
        )
    else:
        lines.append(f"- Primary Topic: {topics[0]}")

    lines.append("")

    for topic in topics:
        cfg = TOPIC_PROMPT_TEMPLATES.get(topic)
        if not cfg:
            continue
        score = all_scores.get(topic, 0.0)
        lines.append(f"### Domain: {cfg['domain']} (confidence: {score:.0%})")
        lines.append(f"- Instruction   : {cfg['instruction']}")
        lines.append(f"- Key Themes    : {cfg['key_themes']}")
        lines.append(f"- Explore       : {cfg['helpful_prompts']}")
        if "caution" in cfg:
            lines.append(f"- CAUTION       : {cfg['caution']}")
        lines.append("")

    return "\n".join(lines)
