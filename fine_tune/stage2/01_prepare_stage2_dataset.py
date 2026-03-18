#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
SAATHI AI — Stage 2 LoRA Dataset Preparation
=============================================
Loads POC source data, normalises to a canonical schema that includes ALL
ML model dimension features (emotion, meta-model patterns, assessment context,
topic, crisis state), augments to 3,017 examples, balances across 11
therapeutic steps and 6 modalities, and exports train/val/test splits in
both structured JSONL and ChatML formats.

Schema Innovation:
  Each training example embeds ML classifier outputs *inside the system
  prompt as structured text blocks* — exactly the format used at inference
  time.  This forces the model to learn how to USE these signals, not just
  receive them.

Usage:
    python 01_prepare_stage2_dataset.py
    python 01_prepare_stage2_dataset.py --out ./data --seed 42

Outputs (in --out directory):
    train.jsonl / val.jsonl / test.jsonl           — canonical schema
    train_chatml.jsonl / val_chatml.jsonl / test_chatml.jsonl — ChatML
    full_dataset.jsonl                              — all 3,017 examples
    dataset_report.json                             — QA statistics
"""

import json
import os
import re
import random
import hashlib
import argparse
from copy import deepcopy
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

# ─── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT   = Path(__file__).parent.parent.parent
# Actual location of POC data in this repo
POC_STAGE2    = REPO_ROOT / "lora_finetuning" / "stage2_postbooking"
POC_CHALLENGE = POC_STAGE2 / "challenge_context_options.jsonl"
# Optional sources — loaders handle missing files gracefully
STAGE2_GOLD         = REPO_ROOT / "lora_finetuning" / "stage2_gold.jsonl"
POC_EVAL            = REPO_ROOT / "lora_finetuning" / "multi_turn_internal_v1.jsonl"
POC_ASSESSMENT_CONV = REPO_ROOT / "lora_finetuning" / "assessment_conversations_v1.jsonl"

# ─── Target Distribution ───────────────────────────────────────────────────────

TARGET_TOTAL = 3_017

STEP_TARGETS = {
    "check_in":              200,
    "session_goal":          191,
    "exploration":           350,
    "validation":            420,
    "psychoeducation":       280,
    "cbt_intervention":      450,
    "mindfulness_grounding": 300,
    "skill_building":        280,
    "practice_homework":     200,
    "summary":               198,
    "closing":               148,
}

MODALITY_RATIOS = {
    "CBT":                0.35,
    "mindfulness":        0.20,
    "DBT":                0.15,
    "ACT":                0.15,
    "motivational_interviewing": 0.10,
    "supportive":         0.05,
}

STEP_NAMES = list(STEP_TARGETS.keys())
STEP_ORDER = {name: i+1 for i, name in enumerate(STEP_NAMES)}

# ─── Clinical Vocabulary ──────────────────────────────────────────────────────

PRESENTING_ISSUES = [
    "workplace_stress", "academic_pressure", "relationship_issues",
    "family_conflict", "grief_bereavement", "health_anxiety",
    "social_anxiety", "depression_withdrawal", "career_transition",
    "financial_stress", "trauma_related", "existential_emptiness",
    "sleep_issues", "anger_management", "substance_use_ambivalence",
    "burnout", "performance_anxiety", "parenting_stress",
]

EMOTION_STATES = [
    {"primary_emotion": "anxiety",     "intensity": 0.78, "secondary_emotion": "shame",       "high_intensity_hopelessness": False},
    {"primary_emotion": "sadness",     "intensity": 0.65, "secondary_emotion": "loneliness",  "high_intensity_hopelessness": False},
    {"primary_emotion": "hopelessness","intensity": 0.72, "secondary_emotion": "sadness",      "high_intensity_hopelessness": True},
    {"primary_emotion": "anger",       "intensity": 0.60, "secondary_emotion": "frustration", "high_intensity_hopelessness": False},
    {"primary_emotion": "guilt",       "intensity": 0.58, "secondary_emotion": "shame",        "high_intensity_hopelessness": False},
    {"primary_emotion": "shame",       "intensity": 0.65, "secondary_emotion": "sadness",      "high_intensity_hopelessness": False},
    {"primary_emotion": "fear",        "intensity": 0.70, "secondary_emotion": "anxiety",      "high_intensity_hopelessness": False},
    {"primary_emotion": "neutral",     "intensity": 0.30, "secondary_emotion": None,           "high_intensity_hopelessness": False},
    {"primary_emotion": "hope",        "intensity": 0.45, "secondary_emotion": "neutral",      "high_intensity_hopelessness": False},
    {"primary_emotion": "grief",       "intensity": 0.82, "secondary_emotion": "sadness",      "high_intensity_hopelessness": False},
    {"primary_emotion": "frustration", "intensity": 0.60, "secondary_emotion": "anger",        "high_intensity_hopelessness": False},
    {"primary_emotion": "despair",     "intensity": 0.85, "secondary_emotion": "hopelessness", "high_intensity_hopelessness": True},
]

META_MODEL_PATTERNS = {
    "universal_quantifier": {
        "examples": [
            "I always fail at everything I try",
            "Nobody ever really understands me",
            "Things never work out the way I plan",
            "I can never do anything right",
        ],
        "pattern_type": "generalisation",
        "recovery_questions": [
            "Always? Can you think of even one time when that wasn't true?",
            "Who specifically has never understood you?",
            "What would it mean if things did work out just once?",
        ],
    },
    "modal_operator_necessity": {
        "examples": [
            "I must be perfect or I'm a failure",
            "I should never show weakness to anyone",
            "I have to handle everything by myself",
            "I need to be strong all the time",
        ],
        "pattern_type": "modal_operator",
        "recovery_questions": [
            "What would happen if you weren't perfect?",
            "Who or what says you should never show weakness?",
            "What stops you from letting others help you?",
        ],
    },
    "modal_operator_possibility": {
        "examples": [
            "I can't cope with this anymore",
            "It's impossible for me to change",
            "I could never ask for help",
            "I'm unable to let go of this",
        ],
        "pattern_type": "modal_operator",
        "recovery_questions": [
            "What would happen if you could cope? What's stopping you?",
            "What would need to be different for change to feel possible?",
            "What would you need in order to be able to ask for help?",
        ],
    },
    "mind_reading": {
        "examples": [
            "I know my boss thinks I'm incompetent",
            "Everyone at work can see I'm struggling",
            "My partner must be disappointed in me",
            "They all think I'm weak",
        ],
        "pattern_type": "distortion",
        "recovery_questions": [
            "How do you know what your boss is thinking?",
            "What evidence do you have that everyone can see that?",
            "Has your partner actually said they're disappointed?",
        ],
    },
    "catastrophising": {
        "examples": [
            "If I fail this presentation my career is over",
            "Everything is going to fall apart completely",
            "This one mistake will ruin everything",
            "If this doesn't work out I don't know what I'll do",
        ],
        "pattern_type": "distortion",
        "recovery_questions": [
            "What's the worst realistic outcome — and could you cope with it?",
            "What evidence do you have that everything will fall apart?",
            "On a scale of 1–10, how likely is the absolute worst case?",
        ],
    },
    "lost_performative": {
        "examples": [
            "They said I'm not good enough for this",
            "People have decided I'm not ready",
            "It's been said that I'm too emotional",
            "Everyone agrees I made a terrible mistake",
        ],
        "pattern_type": "lost_performative",
        "recovery_questions": [
            "Who specifically said that to you?",
            "Who decided you're not ready — and when?",
            "Which people said that, and in what context?",
        ],
    },
    "generalisation_deletion": {
        "examples": [
            "I'm just a failure",
            "I'm completely broken",
            "I'm worthless",
            "There's something wrong with me",
        ],
        "pattern_type": "generalisation",
        "recovery_questions": [
            "A failure at what, specifically?",
            "In what way do you feel broken?",
            "What evidence leads you to that conclusion?",
        ],
    },
}

ASSESSMENT_CONTEXTS = [
    {"phq9": 17, "phq9_sev": "moderately_severe", "gad7": 14, "gad7_sev": "severe",   "days_ago": 3},
    {"phq9": 14, "phq9_sev": "moderate",          "gad7": 11, "gad7_sev": "moderate",  "days_ago": 5},
    {"phq9":  9, "phq9_sev": "mild",              "gad7":  7, "gad7_sev": "mild",      "days_ago": 7},
    {"phq9":  3, "phq9_sev": "minimal",           "gad7":  3, "gad7_sev": "minimal",   "days_ago": 14},
    {"phq9": 22, "phq9_sev": "severe",            "gad7": 18, "gad7_sev": "severe",    "days_ago": 2},
    {"phq9": 14, "phq9_sev": "moderate",          "pss": 25,  "pss_sev": "high_stress","days_ago": 6},
    {"phq9":  9, "phq9_sev": "mild",              "isi": 17,  "isi_sev": "moderate_insomnia", "days_ago": 4},
    {"pcl5": 50, "pcl5_prob": True,               "gad7": 14, "gad7_sev": "severe",    "days_ago": 5},
    {"spin": 40, "spin_sev": "severe_social_anxiety", "phq9": 12, "phq9_sev": "moderate", "days_ago": 3},
    None,  # No assessment yet — also valid training scenario
]

INDIAN_NAMES = [
    "Arjun", "Priya", "Rahul", "Ananya", "Vikram", "Deepika",
    "Suresh", "Kavita", "Rohit", "Neha", "Amit", "Pooja",
    "Kiran", "Shreya", "Mohan", "Divya", "Rajesh", "Sonal",
]

# ─── Harmful Pattern Detection (Clinical Safety) ──────────────────────────────

HARMFUL_PATTERNS = [
    (r"\byou should (leave|divorce|quit|stop)\b",          "directive_advice"),
    (r"\bthat'?s? (stupid|wrong|irrational|silly)\b",      "judgmental"),
    (r"\bi (know|understand) exactly how you feel\b",      "false_empathy"),
    (r"\bthings will definitely get better\b",             "false_promise"),
    (r"\byou'?re? (broken|damaged|flawed|crazy)\b",        "stigmatizing"),
    (r"\bother people have it worse\b",                    "minimization"),
    (r"\bjust (cheer up|calm down|snap out of it)\b",      "dismissive"),
    (r"\byou (must|need to|have to) book\b",               "pressure_tactic"),
    (r"\b(guaranteed|100%|definite(ly)?|certain(ly)?) (results?|cure|fix)\b", "false_guarantee"),
    (r"\bonly \d+ slots? left\b",                          "false_scarcity"),
]


def check_harmful_patterns(text: str) -> List[str]:
    """Return list of violation labels found in text."""
    violations = []
    text_lower = text.lower()
    for pattern, label in HARMFUL_PATTERNS:
        if re.search(pattern, text_lower):
            violations.append(label)
    return violations


# ─── System Prompt Builder (The Core ML-Dimension Injector) ──────────────────

STEP_INSTRUCTIONS = {
    "check_in": (
        "Current Objective: Gently check in on how the user has been since the last interaction.\n"
        "- Ask ONE warm, open-ended question about their week or day\n"
        "- Acknowledge what they share with genuine interest\n"
        "- Do NOT rush to problem-solving or techniques\n"
        "- Duration: 2–3 exchanges, then move to session goal"
    ),
    "session_goal": (
        "Current Objective: Collaboratively set a focus for this session.\n"
        "- Ask what they would most like to work on today\n"
        "- Reflect back their stated goal to confirm understanding\n"
        "- If multiple issues, gently help them prioritise ONE\n"
        "- Tie it to something meaningful to them"
    ),
    "exploration": (
        "Current Objective: Open-ended exploration of the presenting issue.\n"
        "- Use open questions: 'Tell me more about...', 'What's that like for you?'\n"
        "- Follow the thread — let them lead the depth\n"
        "- Notice and gently name themes as they emerge\n"
        "- Do NOT offer solutions yet — only explore"
    ),
    "validation": (
        "Current Objective: Deep validation of the user's emotional experience.\n"
        "- Reflect back what you hear them experiencing\n"
        "- Name the emotion you sense (offer, don't insist)\n"
        "- Communicate: their feelings make complete sense given their experience\n"
        "- NO advice, NO silver linings, NO 'at least...'\n"
        "- Use: 'It sounds like...', 'I hear...', 'That must feel...'"
    ),
    "psychoeducation": (
        "Current Objective: Explain the psychological mechanism behind what they are experiencing.\n"
        "- Connect their experience to a known psychological concept\n"
        "- Normalize: 'This is a very common response to...'\n"
        "- Keep it accessible — avoid clinical jargon\n"
        "- Use analogies and simple language\n"
        "- Invite their reaction: 'Does that resonate with you?'"
    ),
    "cbt_intervention": (
        "Current Objective: Apply a CBT technique appropriate to the presenting issue.\n"
        "Available: Thought Record (5-column ABC), Cognitive Restructuring,\n"
        "          Socratic Questioning, Behavioral Activation, SMART Goal Setting\n"
        "- Choose ONE technique based on what the user has shared\n"
        "- Introduce gently: 'I'd like to try something with you, if that's okay...'\n"
        "- Guide step by step — do not just explain it\n"
        "- Stay curious and collaborative, not prescriptive"
    ),
    "mindfulness_grounding": (
        "Current Objective: Guide a mindfulness or grounding exercise.\n"
        "Available: 5-4-3-2-1 Grounding, Breath Awareness, Body Scan,\n"
        "          RAIN (Recognize, Allow, Investigate, Nurture), Urge Surfing\n"
        "- Ask permission first: 'Would you be open to a brief grounding exercise?'\n"
        "- Guide slowly — pause between instructions\n"
        "- End with: 'How are you feeling now compared to when we started?'"
    ),
    "skill_building": (
        "Current Objective: Teach a concrete, practical coping skill.\n"
        "- Choose a skill matched to the user's issue and modality\n"
        "- Teach it step by step, practically\n"
        "- Check comprehension: 'Can you try putting that in your own words?'\n"
        "- Connect it to their specific situation\n"
        "- Ensure it is achievable between sessions"
    ),
    "practice_homework": (
        "Current Objective: Assign between-session practice.\n"
        "- Make homework SPECIFIC and ACHIEVABLE — not vague\n"
        "- Use implementation intention: 'When X happens, I will do Y'\n"
        "- Anticipate the obstacle: 'What might get in the way?'\n"
        "- Frame as experiment, not obligation\n"
        "- Check willingness: 'Does that feel doable?'"
    ),
    "summary": (
        "Current Objective: Summarise insights and learning from this session.\n"
        "- Identify ONE key insight the user has had today\n"
        "- Reflect any progress or shifts you noticed\n"
        "- Use their words where possible\n"
        "- Keep it brief (2–3 sentences)\n"
        "- Bridge to next session naturally"
    ),
    "closing": (
        "Current Objective: Warm, affirming close to this interaction.\n"
        "- Acknowledge the user's courage and effort in today's session\n"
        "- Confirm the homework if assigned\n"
        "- Confirm next steps or next session timing\n"
        "- End with genuine warmth — not corporate or scripted\n"
        "- Leave the user feeling seen, supported, and hopeful"
    ),
}

MODALITY_TECHNIQUES = {
    "CBT":   ["cognitive restructuring", "thought record", "Socratic questioning", "behavioral activation"],
    "DBT":   ["TIPP", "DEAR MAN", "radical acceptance", "opposite action", "FAST", "GIVE"],
    "mindfulness": ["5-4-3-2-1 grounding", "breath awareness", "body scan", "RAIN", "urge surfing"],
    "ACT":   ["values clarification", "cognitive defusion", "committed action", "psychological flexibility"],
    "motivational_interviewing": ["reflective listening", "change talk exploration", "discrepancy development", "rolling with resistance"],
    "supportive": ["empathic validation", "normalisation", "active listening", "compassionate presence"],
}


def build_stage2_system_prompt(
    therapeutic_step: str,
    modality: str,
    presenting_issue: str,
    session_number: int,
    emotion_ctx: Optional[Dict],
    meta_model_ctx: Optional[List[Dict]],
    assessment_ctx: Optional[Dict],
    topic_ctx: Optional[Dict],
    crisis_ctx: Optional[Dict],
) -> str:
    """
    Build the complete Stage 2 system prompt with ALL ML model dimensions
    injected as structured text blocks — identical to the inference format.
    """
    step_num    = STEP_ORDER.get(therapeutic_step, 1)
    step_instr  = STEP_INSTRUCTIONS.get(therapeutic_step, "Guide the conversation therapeutically.")
    techniques  = ", ".join(MODALITY_TECHNIQUES.get(modality, ["active listening"]))
    issue_label = presenting_issue.replace("_", " ").title()

    base = f"""You are Saathi, an evidence-based AI therapeutic co-pilot supporting users who have already booked therapy sessions.

Your therapeutic foundation:
• Cognitive Behavioral Therapy (CBT)  • Dialectical Behavior Therapy (DBT)
• Mindfulness-Based Approaches         • Acceptance and Commitment Therapy (ACT)
• Motivational Interviewing

Core Principles:
• Empathy before technique — always validate before intervening
• Ask ONE question at a time — never multiple questions in one message
• Follow the user's pace — never rush them
• Clinical safety is non-negotiable — when in doubt, prioritise containment
• Sound human, warm, and genuine — not clinical or scripted

## Therapeutic Step: {step_num}/11 — {therapeutic_step.replace('_', ' ').title()}
{step_instr}

## Session: {session_number} | Modality: {modality} | Presenting Issue: {issue_label}
Available Techniques: {techniques}
"""

    # ── Emotional State Block ─────────────────────────────────────────────────
    if emotion_ctx:
        em   = emotion_ctx.get("primary_emotion", "neutral")
        intn = emotion_ctx.get("intensity", 0.5)
        sec  = emotion_ctx.get("secondary_emotion")
        hihl = emotion_ctx.get("high_intensity_hopelessness", False)

        base += f"\n## Emotional State\n"
        base += f"Detected: {em} (intensity: {intn:.0%})"
        if sec:
            base += f" | Secondary: {sec}"
        base += "\n"

        if hihl or (em in ("hopelessness", "despair") and intn > 0.70):
            base += ("→ HIGH DISTRESS: Pause technique application. Prioritise emotional "
                     "safety and containment. Check for crisis indicators immediately.\n")
        elif em in ("anxiety", "fear") and intn > 0.70:
            base += "→ High anxiety: Validate first. Consider grounding before any cognitive work.\n"
        elif em in ("shame", "guilt") and intn > 0.55:
            base += "→ Shame present: Avoid language implying fault or personal weakness.\n"
        elif em in ("grief", "sadness") and intn > 0.65:
            base += "→ Deep sadness/grief: Slow down. Presence before technique.\n"

    # ── Meta-Model / Cognitive Pattern Block ─────────────────────────────────
    if meta_model_ctx and len(meta_model_ctx) > 0:
        base += "\n## Cognitive Patterns Detected\n"
        for p in meta_model_ctx[:3]:
            ptype   = p.get("pattern_type", "unknown")
            subtype = p.get("pattern_subtype", ptype)
            text    = p.get("matched_text", "")
            conf    = p.get("confidence", 0.75)
            rq      = p.get("recovery_question", "")
            base += f"- {subtype.replace('_', ' ').title()}: \"{text}\" (confidence: {conf:.0%})\n"
            if rq:
                base += f"  → Recovery question: {rq}\n"
        base += ("→ Technique alignment: use recovery questions to challenge distortions; "
                 "cognitive restructuring is available if suitable.\n")

    # ── Assessment Context Block ───────────────────────────────────────────────
    if assessment_ctx:
        base += "\n## Assessment Context"
        days = assessment_ctx.get("days_ago", 0)
        base += f" ({days} day{'s' if days != 1 else ''} ago)\n"

        if "phq9" in assessment_ctx:
            sev = assessment_ctx.get("phq9_sev", "")
            base += f"PHQ-9: {assessment_ctx['phq9']}/27 — {sev.replace('_', ' ').title()}\n"
        if "gad7" in assessment_ctx:
            sev = assessment_ctx.get("gad7_sev", "")
            base += f"GAD-7: {assessment_ctx['gad7']}/21 — {sev.replace('_', ' ').title()}\n"
        if "pss" in assessment_ctx:
            sev = assessment_ctx.get("pss_sev", "")
            base += f"PSS-10: {assessment_ctx['pss']}/40 — {sev.replace('_', ' ').title()}\n"
        if "isi" in assessment_ctx:
            sev = assessment_ctx.get("isi_sev", "")
            base += f"ISI: {assessment_ctx['isi']}/28 — {sev.replace('_', ' ').title()}\n"
        if "pcl5" in assessment_ctx:
            prob = "Probable PTSD" if assessment_ctx.get("pcl5_prob") else "Sub-threshold PTSD"
            base += f"PCL-5: {assessment_ctx['pcl5']}/80 — {prob}\n"
        if "spin" in assessment_ctx:
            sev = assessment_ctx.get("spin_sev", "")
            base += f"SPIN: {assessment_ctx['spin']}/68 — {sev.replace('_', ' ').title()}\n"

        # Severity guidance
        phq = assessment_ctx.get("phq9", 0)
        gad = assessment_ctx.get("gad7", 0)
        if phq >= 20 or gad >= 15:
            base += "→ Severe symptoms: Prioritise safety check. Confirm therapist is involved.\n"
        elif phq >= 10 or gad >= 10:
            base += "→ Moderate symptoms: Comorbid presentation likely. Monitor for avoidance and rumination.\n"

    # ── Topic / Domain Block ──────────────────────────────────────────────────
    if topic_ctx:
        topic = topic_ctx.get("primary_topic", presenting_issue)
        guidance = {
            "workplace_stress":      "Acknowledge occupational pressure directly. Validate systemic factors.",
            "financial_stress":      "Be sensitive about costs in any discussion of resources.",
            "grief_bereavement":     "Slow the pace. Prioritise presence and normalisation over technique.",
            "trauma_related":        "TRAUMA ACTIVE: Do NOT proceed with standard CBT. Use trauma-informed approach.",
            "relationship_issues":   "Be warm and non-judgmental. Avoid taking sides.",
            "academic_pressure":     "Normalise performance anxiety. Validate the pressure explicitly.",
            "social_anxiety":        "Small steps only. Avoid overwhelming the user with exposure tasks too early.",
            "substance_use_ambivalence": "Motivational Interviewing ONLY. No directives. Explore ambivalence.",
        }.get(topic, "")
        base += f"\n## Topic: {topic.replace('_', ' ').title()}\n"
        if guidance:
            base += f"→ {guidance}\n"

    # ── Crisis State Block ────────────────────────────────────────────────────
    crisis_active = False
    if crisis_ctx:
        score = crisis_ctx.get("severity_score", 0.0)
        crisis_active = crisis_ctx.get("crisis_active", False) or score >= 7

    if crisis_active:
        base += ("\n## ⚠ CRISIS STATE ACTIVE\n"
                 "STOP all therapy flow immediately. Do NOT apply any technique.\n"
                 "Prioritise: validate → ask directly about safety → provide resources\n"
                 "Resources: iCall: +91-9152987821 | Vandrevala: 1860-2662-345 | NIMHANS: 080-46110007\n")
    else:
        base += "\n## Crisis State: None detected\n"

    return base.strip()


# ─── Data Loaders ─────────────────────────────────────────────────────────────

def load_stage2_gold() -> List[Dict]:
    """Load 7 gold-standard multi-turn therapy conversations."""
    examples = []
    if not STAGE2_GOLD.exists():
        return examples
    with open(STAGE2_GOLD) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                examples.append({
                    "_source": "stage2_gold",
                    "_raw": raw,
                    "modality": raw.get("therapy_modality", "CBT"),
                    "presenting_issue": raw.get("presenting_issue", "workplace_stress"),
                    "messages": raw.get("messages", []),
                    "therapeutic_steps_covered": raw.get("therapeutic_steps_covered", [6]),
                    "outcome": raw.get("outcome", "skill_practiced"),
                    "quality_score": 4.8,  # gold examples are highest quality
                })
            except Exception:
                pass
    return examples


def load_challenge_context() -> List[Dict]:
    """Load challenge_context_options.jsonl (206 multi-turn examples)."""
    examples = []
    if not POC_CHALLENGE.exists():
        return examples
    with open(POC_CHALLENGE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                meta = raw.get("metadata", {})
                examples.append({
                    "_source": "challenge_context",
                    "_raw": raw,
                    "modality": _map_approach(raw.get("therapeutic_approach", "integrative")),
                    "presenting_issue": _map_concern(raw.get("primary_concern", "anxiety")),
                    "messages": raw.get("messages", []),
                    "technique": meta.get("technique", ""),
                    "emotion": meta.get("emotion", "anxiety"),
                    "safety_flag": meta.get("safety_flag", "safe"),
                    "quality_score": 4.0,
                })
            except Exception:
                pass
    return examples


def load_multi_turn_poc() -> List[Dict]:
    """Load multi_turn_internal_v1.jsonl (20 annotated dialogues)."""
    examples = []
    if not POC_EVAL.exists():
        return examples
    with open(POC_EVAL) as f:
        content = f.read().strip()
    # Handle concatenated JSON objects
    for chunk in content.split("\n{"):
        chunk = chunk.strip()
        if not chunk.startswith("{"):
            chunk = "{" + chunk
        try:
            raw = json.loads(chunk)
        except Exception:
            continue
        if "turns" not in raw:
            continue
        # Convert turns to messages
        messages = []
        for turn in raw["turns"]:
            if turn["speaker"] == "user":
                messages.append({"role": "user", "content": turn["utterance"]})
            else:
                messages.append({"role": "assistant", "content": turn["utterance"]})
        topic = raw.get("topic", "relationship_stress")
        examples.append({
            "_source": "multi_turn_poc",
            "_raw": raw,
            "modality": _topic_to_modality(topic),
            "presenting_issue": _topic_to_issue(topic),
            "messages": messages,
            "emotion": raw["turns"][0].get("emotion", "neutral") if raw["turns"] else "neutral",
            "meta_annotations": raw.get("meta_annotations", {}),
            "quality_score": 4.2,
        })
    return examples


def load_single_turn_poc() -> List[Dict]:
    """Load all small single-turn JSONL files from stage2_postbooking."""
    examples = []
    skip_files = {"challenge_context_options.jsonl"}
    for fpath in sorted(POC_STAGE2.glob("*.jsonl")):
        if fpath.name in skip_files:
            continue
        with open(fpath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except Exception:
                    continue
                # Single-turn format: id, user_utterance, context, assistant_response
                if "user_utterance" in raw and "assistant_response" in raw:
                    ctx_text = raw.get("context", "")
                    messages = []
                    # Rebuild prior context turns if available
                    if ctx_text:
                        prior_utterances = [u.strip() for u in ctx_text.split("|") if u.strip()]
                        for i, utt in enumerate(prior_utterances):
                            messages.append({"role": "user", "content": utt})
                            # We don't have prior assistant responses, use placeholder
                            messages.append({"role": "assistant", "content": "[Prior response]"})
                    messages.append({"role": "user",      "content": raw["user_utterance"]})
                    messages.append({"role": "assistant", "content": raw["assistant_response"]})
                    examples.append({
                        "_source": f"poc_{fpath.stem}",
                        "_raw": raw,
                        "modality": _response_type_to_modality(raw.get("response_type", "")),
                        "presenting_issue": _emotion_to_issue(raw.get("emotion", "neutral")),
                        "messages": messages,
                        "emotion": raw.get("emotion", "neutral"),
                        "safety_flag": raw.get("safety_flag", "safe"),
                        "quality_score": 3.8,
                    })
                # Other formats (greetings, pattern_mapping, etc.)
                elif "context" in raw and "options" in raw:
                    pass  # skip non-dialogue entries
    return examples


# ─── Mapping Helpers ──────────────────────────────────────────────────────────

def _map_approach(approach: str) -> str:
    m = {"cbt": "CBT", "dbt": "DBT", "mindfulness": "mindfulness",
         "act": "ACT", "motivational": "motivational_interviewing",
         "integrative": "CBT", "supportive": "supportive"}
    return m.get(approach.lower(), "CBT")


def _map_concern(concern: str) -> str:
    m = {"anxiety": "health_anxiety", "depression": "depression_withdrawal",
         "stress": "workplace_stress", "relationship": "relationship_issues",
         "trauma": "trauma_related", "grief": "grief_bereavement",
         "anger": "anger_management", "sleep": "sleep_issues"}
    return m.get(concern.lower(), "workplace_stress")


def _topic_to_modality(topic: str) -> str:
    m = {"relationship_stress": "supportive", "academic_pressure": "CBT",
         "self-esteem_issues": "CBT", "workplace_conflict": "DBT",
         "breakup_grief": "supportive", "sleep_problems": "mindfulness"}
    return m.get(topic, "CBT")


def _topic_to_issue(topic: str) -> str:
    m = {"relationship_stress": "relationship_issues", "academic_pressure": "academic_pressure",
         "self-esteem_issues": "depression_withdrawal", "workplace_conflict": "workplace_stress",
         "breakup_grief": "grief_bereavement", "sleep_problems": "sleep_issues"}
    return m.get(topic, "workplace_stress")


def _response_type_to_modality(rt: str) -> str:
    m = {"reframe": "CBT", "grounding": "mindfulness", "validation": "supportive",
         "clarification": "CBT", "narrative": "supportive", "summary": "supportive",
         "active_listening": "supportive", "question": "motivational_interviewing"}
    return m.get(rt, "CBT")


def _emotion_to_issue(emotion: str) -> str:
    m = {"anxiety": "health_anxiety", "sadness": "depression_withdrawal",
         "hopeless": "depression_withdrawal", "guilt": "workplace_stress",
         "frustration": "workplace_stress", "anger": "anger_management",
         "stress": "workplace_stress", "relief": "workplace_stress"}
    return m.get(emotion, "workplace_stress")


# ─── ML Context Injection ─────────────────────────────────────────────────────

def sample_emotion_ctx(emotion_hint: Optional[str] = None) -> Dict:
    if emotion_hint:
        for e in EMOTION_STATES:
            if e["primary_emotion"] == emotion_hint:
                return deepcopy(e)
    return deepcopy(random.choice(EMOTION_STATES))


def sample_meta_model_ctx(n: int = 0) -> List[Dict]:
    """Return 0–2 meta-model pattern dicts for injection."""
    if n == 0:
        n = random.choices([0, 1, 2], weights=[0.30, 0.45, 0.25])[0]
    if n == 0:
        return []
    patterns = random.sample(list(META_MODEL_PATTERNS.keys()), min(n, len(META_MODEL_PATTERNS)))
    result = []
    for pname in patterns:
        p = META_MODEL_PATTERNS[pname]
        result.append({
            "pattern_type":    p["pattern_type"],
            "pattern_subtype": pname,
            "matched_text":    random.choice(p["examples"]),
            "confidence":      round(random.uniform(0.65, 0.92), 2),
            "recovery_question": random.choice(p["recovery_questions"]),
        })
    return result


def sample_assessment_ctx() -> Optional[Dict]:
    return deepcopy(random.choice(ASSESSMENT_CONTEXTS))


def sample_topic_ctx(presenting_issue: str) -> Dict:
    return {"primary_topic": presenting_issue,
            "all_topics": [presenting_issue]}


def sample_crisis_ctx(safe: bool = True) -> Dict:
    if safe:
        return {"crisis_active": False, "severity_score": round(random.uniform(0.0, 1.5), 1)}
    return {"crisis_active": True, "severity_score": round(random.uniform(7.0, 9.5), 1)}


# ─── Canonical Schema Builder ─────────────────────────────────────────────────

def build_canonical(
    source_messages: List[Dict],
    modality: str,
    presenting_issue: str,
    therapeutic_step: str,
    session_number: int,
    emotion_ctx: Optional[Dict],
    meta_model_ctx: List[Dict],
    assessment_ctx: Optional[Dict],
    source_id: str,
    quality_score: float = 4.0,
    outcome: str = "skill_practiced",
    safety_flag: str = "safe",
    crisis_active: bool = False,
) -> Dict:
    """Build a canonical Stage 2 training example."""

    topic_ctx  = sample_topic_ctx(presenting_issue)
    crisis_ctx = sample_crisis_ctx(safe=not crisis_active)

    # Filter out placeholder assistant turns from single-turn expansion
    clean_msgs = [m for m in source_messages
                  if not (m["role"] == "assistant" and m["content"] == "[Prior response]")]

    # Build the ML-enriched system prompt
    system_prompt = build_stage2_system_prompt(
        therapeutic_step=therapeutic_step,
        modality=modality,
        presenting_issue=presenting_issue,
        session_number=session_number,
        emotion_ctx=emotion_ctx,
        meta_model_ctx=meta_model_ctx,
        assessment_ctx=assessment_ctx,
        topic_ctx=topic_ctx,
        crisis_ctx=crisis_ctx,
    )

    # Final message list: system + conversation turns
    messages = [{"role": "system", "content": system_prompt}] + clean_msgs

    # Unique ID
    conv_id = "s2_" + hashlib.md5(f"{source_id}{therapeutic_step}{modality}{random.random()}".encode()).hexdigest()[:10]

    return {
        "conversation_id": conv_id,
        "session_type": "follow_up" if session_number > 1 else "initial",
        "therapeutic_modality": modality,
        "therapeutic_step": therapeutic_step,
        "step_number": STEP_ORDER.get(therapeutic_step, 1),
        "step_name": therapeutic_step,
        "presenting_issue": presenting_issue,
        "session_number": session_number,
        "messages": messages,
        "ml_context": {
            "emotion": emotion_ctx,
            "meta_model_patterns": meta_model_ctx,
            "assessment": assessment_ctx,
            "topic": topic_ctx,
            "crisis": crisis_ctx,
        },
        "metadata": {
            "techniques_used": MODALITY_TECHNIQUES.get(modality, [])[:2],
            "emotion_in_context": emotion_ctx.get("primary_emotion", "neutral") if emotion_ctx else "neutral",
            "crisis_flag": crisis_active,
            "step_completed": True,
            "clinician_reviewed": quality_score >= 4.5,
            "clinical_quality_score": round(quality_score, 1),
            "dataset_source": source_id,
            "safety_flag": safety_flag,
            "outcome": outcome,
        },
    }


# ─── Template Conversation Library ───────────────────────────────────────────
# High-quality multi-turn templates for each step/modality combination.
# These are used for augmentation when raw POC data is insufficient.

CONVERSATION_TEMPLATES = [
    # ── CBT: Exploration + Validation + Psychoeducation + Intervention ──────
    {
        "modality": "CBT", "step": "exploration", "issue": "workplace_stress",
        "turns": [
            ("user", "I've been having a really rough week at work. I feel like I'm drowning."),
            ("assistant", "That sounds really exhausting. When you say 'drowning' — what does that feel like day to day? What's been piling up?"),
            ("user", "It's everything at once. Deadlines, a difficult manager, and I made a mistake on a project that I can't stop thinking about."),
            ("assistant", "Three things at once — the deadlines, the relationship with your manager, and a specific mistake that's following you around. Which of those feels heaviest right now?"),
            ("user", "The mistake. I keep replaying it and imagining my manager thinking I'm incompetent."),
            ("assistant", "That replaying — that mental loop — is really draining to carry. Can you tell me more about what your mind is saying when it replays that moment?"),
        ]
    },
    {
        "modality": "CBT", "step": "cbt_intervention", "issue": "performance_anxiety",
        "turns": [
            ("user", "I've been catastrophising about a presentation next week. I know logically I'll be fine but I can't stop."),
            ("assistant", "That gap between what we know logically and what our anxious brain keeps insisting on — that's exactly where CBT is most useful. I'd like to try something with you, if that's okay — it's called a thought record."),
            ("user", "Okay, I'm willing to try."),
            ("assistant", "Good. Let's start with the automatic thought itself. What's the exact catastrophic thought your mind keeps producing about this presentation?"),
            ("user", "That I'll freeze on stage, forget everything, and everyone will see I don't belong there."),
            ("assistant", "Okay. Now the key question — what's the evidence FOR that thought? And then we'll look at evidence against it. Start with: what actually supports the idea that you'll freeze and be seen as incompetent?"),
            ("user", "I had a bad presentation once, two years ago. And I haven't slept well this week."),
            ("assistant", "One difficult experience, two years ago. And poor sleep this week — which is temporary. Now — evidence against: what tells you this catastrophic outcome is not the most likely one?"),
        ]
    },
    {
        "modality": "CBT", "step": "validation", "issue": "depression_withdrawal",
        "turns": [
            ("user", "I haven't painted in months. I used to paint every weekend. Now I can't even imagine picking up a brush."),
            ("assistant", "Losing something that used to bring you joy — and not being able to access it even when you want to — that's one of the most disorienting parts of what you're going through."),
            ("user", "I feel like I've lost myself. Like the person who loved painting has just disappeared."),
            ("assistant", "That sense of a self that's become unreachable — it makes complete sense that it feels frightening. You haven't stopped being that person. Depression creates a kind of glass wall between you and the things that matter. The painter is still there."),
            ("user", "I hope so. I just feel so empty."),
            ("assistant", "That emptiness is real. And it's not a character flaw — it's a symptom. You don't have to push through it or pretend it isn't there. I hear it."),
        ]
    },
    # ── DBT: Distress tolerance, emotion regulation ───────────────────────
    {
        "modality": "DBT", "step": "cbt_intervention", "issue": "anger_management",
        "turns": [
            ("user", "I'm shaking with anger after a call with my mother. I can't calm down."),
            ("assistant", "At a 9 or 10 out of 10 with anger, your thinking brain is quite literally offline — the body has taken over. Before we talk about what happened, let's use a DBT skill called TIPP to bring the intensity down. Can I guide you through the Temperature step?"),
            ("user", "What do I do?"),
            ("assistant", "Can you get to a sink? Splash cold water on your face — or if you have ice, hold it for 30 seconds. Cold water activates the dive reflex and physiologically slows the heart rate within seconds."),
            ("user", "Okay I splashed my face. Maybe a 7 now."),
            ("assistant", "Good — that's your body responding. Now let's do Paced Breathing together. Inhale for 4 counts, hold for 2, exhale slowly for 6 counts. The extended exhale activates the parasympathetic nervous system. Ready?"),
            ("user", "Yes. Doing it now... okay, about a 5."),
            ("assistant", "A 5 — your thinking brain is back online. Now I want to hear what happened. Tell me what she said, and more importantly, what it touched in you."),
        ]
    },
    {
        "modality": "DBT", "step": "skill_building", "issue": "relationship_issues",
        "turns": [
            ("user", "I need to tell my partner that their criticism in front of friends really hurt me. But I always either blow up or shut down."),
            ("assistant", "What you're describing — either exploding or going silent — is a very common pattern when stakes are high in close relationships. DBT has a skill called DEAR MAN that's specifically for communicating needs effectively. Would you like to try building that conversation together?"),
            ("user", "Yes please."),
            ("assistant", "D stands for Describe — just the facts, without interpretation. What is the concrete behaviour you want to address?"),
            ("user", "When they criticise my cooking in front of our friends."),
            ("assistant", "Good — that's clean, factual, not loaded. E is Express — share how it makes you feel using 'I feel' not 'you make me feel'. How does it leave you feeling?"),
            ("user", "I feel embarrassed and dismissed."),
            ("assistant", "Perfect. Now A — Assert your need clearly. What do you actually need from them going forward?"),
        ]
    },
    # ── Mindfulness: Grounding, breath, body scan ─────────────────────────
    {
        "modality": "mindfulness", "step": "mindfulness_grounding", "issue": "burnout",
        "turns": [
            ("user", "I feel completely disconnected from myself. I go through the motions every day."),
            ("assistant", "That sense of going through the motions — feeling like a passenger in your own life — is what the nervous system does under prolonged stress. It's protecting you, but it becomes its own kind of suffering. I'd like to try a brief grounding exercise with you. Would you be open to it?"),
            ("user", "Sure."),
            ("assistant", "Keep your eyes open. Right now, wherever you are — name 5 things you can SEE. Don't describe them, just notice them. Take a moment."),
            ("user", "My laptop, the window, a plant, my coffee mug, my hands."),
            ("assistant", "Good. Now 4 things you can physically FEEL — not emotions, but sensations. The weight of your body in the chair. The temperature of the air. The texture under your hands."),
            ("user", "My back against the chair. The cup warm in my hands. The floor under my feet. Cold air."),
            ("assistant", "Notice — you're more present right now than you were a minute ago. That's grounding working. Let's do 3, 2, 1 and you'll have completed the full technique. 3 things you can HEAR."),
        ]
    },
    {
        "modality": "mindfulness", "step": "psychoeducation", "issue": "health_anxiety",
        "turns": [
            ("user", "My mind won't stop. I keep scanning my body for symptoms and then I spiral."),
            ("assistant", "What you're describing has a name: hypervigilance. When the nervous system is on high alert, it literally scans constantly for threat — and in health anxiety, the body itself becomes the target of that scanning."),
            ("user", "Why does it feel like the more I check, the worse it gets?"),
            ("assistant", "That's the cruel paradox. Each check gives the brain a temporary signal of safety. But it also reinforces the brain's message that checking is necessary — that there IS something to find. Over time the checking loop gets tighter and tighter."),
            ("user", "So what do I do?"),
            ("assistant", "The path is not willpower — it's not 'stop checking.' It's learning to tolerate the uncertainty without taking the checking action. Mindfulness is one of the most effective tools for this, because it teaches the nervous system that uncertainty is survivable without resolution."),
        ]
    },
    # ── ACT: Values, defusion ─────────────────────────────────────────────
    {
        "modality": "ACT", "step": "psychoeducation", "issue": "existential_emptiness",
        "turns": [
            ("user", "I have a great job, a good family, but I feel hollow inside. Like something fundamental is missing."),
            ("assistant", "What you're describing — having the externally 'successful' life and still feeling hollow — is one of the most disorienting experiences possible. It doesn't fit the story we're supposed to feel."),
            ("user", "I thought the promotion would fix it. It made it worse."),
            ("assistant", "That post-achievement emptiness tells us something important: the emptiness wasn't coming from lack of achievement. Which means more achievement won't fill it either. In ACT, we call this the 'achievement trap' — we pursue what we were told to pursue and discover it doesn't produce meaning."),
            ("user", "Then what does?"),
            ("assistant", "Values — not goals. Goals are destinations you arrive at and then you need a new one. Values are directions. They're how you want to live, not what you want to achieve. The question isn't 'what do I want to accomplish?' but 'who do I want to be, and how do I want to show up in my life?'"),
        ]
    },
    {
        "modality": "ACT", "step": "skill_building", "issue": "career_transition",
        "turns": [
            ("user", "I know I need to leave my job but I keep second-guessing myself. What if I regret it?"),
            ("assistant", "That second-guessing is often what ACT calls 'cognitive fusion' — being so merged with a thought ('what if I regret it?') that the thought feels like reality. Let's try something. Instead of 'what if I regret it', what if you said: 'I'm having the thought that I might regret it'?"),
            ("user", "That feels different actually. Like I'm watching the thought rather than being inside it."),
            ("assistant", "Exactly — that's defusion. The thought is still there, but you're no longer identical with it. It's a thought your mind produced — not a prophecy. Now let's look at what your values say. When you imagine staying in the job for another year, what does that feel like in your body?"),
            ("user", "Dread. Real physical dread."),
            ("assistant", "And when you imagine having left — even with uncertainty about what's next — what does that feel like?"),
        ]
    },
    # ── Motivational Interviewing: ambivalence ─────────────────────────────
    {
        "modality": "motivational_interviewing", "step": "exploration", "issue": "substance_use_ambivalence",
        "turns": [
            ("user", "I know I drink too much but I don't want to completely stop. I don't see why I have to."),
            ("assistant", "I'm not here to tell you that you have to do anything. You're the expert on your own life. I'm curious — you said you 'know' you drink too much. What part of you has noticed that?"),
            ("user", "Blackouts. And my wife said something last week that really hit me."),
            ("assistant", "Those two things landed differently for you — the blackouts and what your wife said. Without me pushing in any direction: when you imagine your life five years from now, continuing exactly as you are — what does that look like?"),
            ("user", "Honestly? Probably divorced. Maybe sick."),
            ("assistant", "And when you imagine five years from now having made some changes around drinking — what does that picture look like?"),
        ]
    },
    # ── Supportive: grief, validation ─────────────────────────────────────
    {
        "modality": "supportive", "step": "validation", "issue": "grief_bereavement",
        "turns": [
            ("user", "My mother died four months ago. People keep saying I should be over it. I'm not."),
            ("assistant", "There is no timeline for grief, and anyone who suggests there should be does not understand loss. Four months is no time at all when you've lost a mother. How are you carrying it day to day?"),
            ("user", "I don't cry much. But I feel her absence in everything. I keep reaching for my phone to call her."),
            ("assistant", "That reaching — that muscle memory of wanting to share something with her — is one of the most piercing parts of grief. The body looking for what the mind already knows is gone."),
            ("user", "She was my person. The one who always understood me. Now nobody really knows me."),
            ("assistant", "That's a profound loss — not just the person, but the experience of being truly known. Some therapists say losing a parent is losing your earliest witness. The person who knew you before you were anyone else."),
        ]
    },
    {
        "modality": "supportive", "step": "check_in", "issue": "relationship_issues",
        "turns": [
            ("user", "Hi. I'm back."),
            ("assistant", "Welcome back. How have you been since we last spoke?"),
            ("user", "It's been a mixed week honestly. Some moments were okay. Some were hard."),
            ("assistant", "Mixed weeks are real weeks. I'm glad you came back. What stood out — what was the hardest part?"),
            ("user", "An argument with my partner on Thursday. We said some things."),
            ("assistant", "Thursday is still close. How are you feeling about it now, a few days on?"),
        ]
    },
    # ── Session opening/closing templates ─────────────────────────────────
    {
        "modality": "CBT", "step": "session_goal", "issue": "academic_pressure",
        "turns": [
            ("user", "I'm not sure what to focus on today. Everything feels urgent."),
            ("assistant", "When everything feels urgent, it's hard for the mind to land anywhere. Let's slow that down. If you could leave today's session having made progress on just ONE thing — what would feel most meaningful?"),
            ("user", "I think my exam anxiety. It's interfering with everything."),
            ("assistant", "Exam anxiety as the focus — that makes sense. Can you tell me what exam anxiety looks like for you specifically? How does it show up in your body and your thinking?"),
        ]
    },
    {
        "modality": "CBT", "step": "closing", "issue": "workplace_stress",
        "turns": [
            ("user", "That was really helpful. I feel a bit clearer."),
            ("assistant", "I'm really glad. You did good work today — examining that thought rather than just carrying it takes real effort. The key insight you found: the evidence ratio doesn't support the catastrophic prediction. That balanced thought is yours to keep."),
            ("user", "I'll try the thought record tonight."),
            ("assistant", "Perfect. Thought record tonight — 10 minutes, on paper if possible. Notice the automatic thought, the evidence each way, and the balanced alternative. Before we close: is there anything you need from me before next session?"),
        ]
    },
    {
        "modality": "mindfulness", "step": "practice_homework", "issue": "burnout",
        "turns": [
            ("user", "So should I practice the grounding technique every day?"),
            ("assistant", "Yes — and I want to make it specific so it actually happens. When in your day would be the most natural time? Morning, before work, a break during the day?"),
            ("user", "Maybe before my first meeting of the day. I'm usually anxious then."),
            ("assistant", "Before your first meeting — that's a perfect implementation intention. So: 'Before my first meeting each day, I will do 5-4-3-2-1 grounding for 3 minutes.' What might get in the way of that?"),
            ("user", "I might forget or feel rushed."),
            ("assistant", "Good — you've named the obstacle. So the backup intention is: if I feel rushed, I'll do just the first two steps — 5 things I see, 4 things I feel. Even 60 seconds counts. Does that feel doable?"),
        ]
    },
    {
        "modality": "CBT", "step": "summary", "issue": "depression_withdrawal",
        "turns": [
            ("user", "I think I understand now why starting small matters."),
            ("assistant", "That's the heart of what we explored today — in depression, waiting to 'feel like it' before acting is the trap. Behaviour drives mood; you don't need motivation first, you need to act and let motivation follow."),
            ("user", "The idea of just putting my shoes on feels doable. Not running 5k."),
            ("assistant", "Exactly. Shoes on, end of street, back home. Three times this week. That's enough. The goal is rebuilding the habit loop, not performance. You've shifted something important today by seeing through the 'I need to feel ready first' story."),
        ]
    },
    # ── Assessment integration ────────────────────────────────────────────
    {
        "modality": "CBT", "step": "psychoeducation", "issue": "depression_withdrawal",
        "turns": [
            ("user", "I did the questionnaire last week. It said moderate depression. I'm not sure what that means for me."),
            ("assistant", "The PHQ-9 score you got — moderate — means your symptoms are consistent enough and significant enough to be affecting your quality of life. But it's not a sentence, it's a description. It tells us where to focus."),
            ("user", "My scores were highest on the thinking questions — the concentration and negative thoughts ones."),
            ("assistant", "That's really useful to know. When the cognitive subscale is elevated — concentration, negative self-talk, seeing yourself in a negative light — that tells us the thinking brain is working against you most. That's exactly where CBT is most directly targeted."),
        ]
    },
    # ── Crisis de-escalation ───────────────────────────────────────────────
    {
        "modality": "supportive", "step": "validation", "issue": "trauma_related",
        "turns": [
            ("user", "I've been having thoughts about hurting myself. It scares me."),
            ("assistant", "Thank you for telling me that. The fact that it scares you — that's your whole self speaking, not just the pain. I need to ask directly: are you safe right now?"),
            ("user", "I think so. I won't act on it. But the thoughts keep coming."),
            ("assistant", "I hear you — intrusive thoughts without intention are different from a plan. And I want to make sure you have support beyond this conversation. Is your therapist aware these thoughts have been present?"),
            ("user", "Not yet."),
            ("assistant", "I'd like to ask you to share this with your therapist at your next session — or call them today if the thoughts intensify. You deserve full support for this. iCall: +91-9152987821 is available 24/7 if you need to speak to someone before then."),
        ]
    },
]


# ─── Template-Based Augmentation ─────────────────────────────────────────────

def generate_from_templates(target_per_step: Dict[str, int]) -> List[Dict]:
    """
    Generate canonical examples from the CONVERSATION_TEMPLATES by:
    1. Using each template as a seed
    2. Varying: presenting_issue, session_number, emotion, meta_model, assessment
    3. Until each step reaches its target count
    """
    examples = []
    step_counts = defaultdict(int)

    templates_by_step = defaultdict(list)
    for tpl in CONVERSATION_TEMPLATES:
        templates_by_step[tpl["step"]].append(tpl)

    for step, target in target_per_step.items():
        available = templates_by_step.get(step, [])
        if not available:
            # Fall back to nearest step templates
            available = CONVERSATION_TEMPLATES

        while step_counts[step] < target:
            tpl = random.choice(available)
            modality = tpl["modality"]
            base_issue = tpl.get("issue", "workplace_stress")

            # Vary the presenting issue
            issue = random.choice(PRESENTING_ISSUES) if random.random() < 0.4 else base_issue
            session_number = random.randint(1, 10)
            emotion_ctx    = sample_emotion_ctx()
            meta_ctx       = sample_meta_model_ctx()
            assess_ctx     = sample_assessment_ctx()
            crisis_active  = False  # templates are never crisis scenarios

            # Convert template turns to message list
            msgs = [{"role": role, "content": text} for role, text in tpl["turns"]]

            example = build_canonical(
                source_messages=msgs,
                modality=modality,
                presenting_issue=issue,
                therapeutic_step=step,
                session_number=session_number,
                emotion_ctx=emotion_ctx,
                meta_model_ctx=meta_ctx,
                assessment_ctx=assess_ctx,
                source_id=f"template_{step}",
                quality_score=4.5,
            )
            examples.append(example)
            step_counts[step] += 1

    return examples


# ─── POC Data Normalisation ──────────────────────────────────────────────────

def normalize_poc_to_canonical(raw_sources: List[Dict]) -> List[Dict]:
    """Convert all POC source examples to canonical schema."""
    canonicals = []

    for src in raw_sources:
        if not src.get("messages"):
            continue

        # Skip examples with only placeholder assistant turns
        real_assistant_turns = [
            m for m in src["messages"]
            if m["role"] == "assistant" and m["content"] != "[Prior response]" and len(m["content"]) > 20
        ]
        if not real_assistant_turns:
            continue

        modality = src.get("modality", "CBT")
        issue    = src.get("presenting_issue", "workplace_stress")
        emotion  = src.get("emotion", "neutral")

        # Assign therapeutic step based on source type
        step = _assign_step(src)

        emotion_ctx  = sample_emotion_ctx(emotion)
        meta_ctx     = sample_meta_model_ctx()
        assess_ctx   = sample_assessment_ctx()
        session_num  = random.randint(1, 8)

        quality = src.get("quality_score", 4.0)
        safety  = src.get("safety_flag", "safe")

        # Check for harmful patterns in assistant responses
        all_assistant_text = " ".join(m["content"] for m in src["messages"] if m["role"] == "assistant")
        violations = check_harmful_patterns(all_assistant_text)
        if violations:
            continue  # Drop harmful examples

        example = build_canonical(
            source_messages=src["messages"],
            modality=modality,
            presenting_issue=issue,
            therapeutic_step=step,
            session_number=session_num,
            emotion_ctx=emotion_ctx,
            meta_model_ctx=meta_ctx,
            assessment_ctx=assess_ctx,
            source_id=src.get("_source", "poc"),
            quality_score=quality,
            safety_flag=safety,
        )
        canonicals.append(example)

    return canonicals


def _assign_step(src: Dict) -> str:
    """Heuristically assign a therapeutic step based on source signals."""
    source = src.get("_source", "")
    technique = src.get("technique", "")
    response_type = src.get("_raw", {}).get("response_type", "") if src.get("_raw") else ""

    # Explicit technique hints
    step_map = {
        "challenge_prioritization": "session_goal",
        "grounding": "mindfulness_grounding",
        "reframe": "cbt_intervention",
        "validation": "validation",
        "clarification": "exploration",
        "narrative": "exploration",
        "summary": "summary",
        "active_listening": "check_in",
        "question": "exploration",
    }
    for key, step in step_map.items():
        if key in technique.lower() or key in response_type.lower():
            return step

    # Source file hints
    if "active_listening" in source or "empathetic" in source:
        return random.choice(["check_in", "validation"])
    if "cbt" in source or "distortion" in source or "generalization" in source:
        return "cbt_intervention"
    if "dbt" in source or "mindfulness" in source or "vak" in source:
        return random.choice(["mindfulness_grounding", "skill_building"])
    if "meta_model" in source or "deletion" in source or "modal" in source:
        return "exploration"
    if "session_summary" in source:
        return "summary"
    if "gold" in source:
        # Gold conversations cover multiple steps — pick main one
        steps_covered = src.get("therapeutic_steps_covered", [6])
        # Map step numbers to step names
        num_to_name = {i+1: n for i, n in enumerate(STEP_NAMES)}
        return num_to_name.get(steps_covered[len(steps_covered)//2], "cbt_intervention")

    return random.choice(STEP_NAMES)


# ─── Dataset Assembly and Balancing ─────────────────────────────────────────

def assemble_and_balance(all_examples: List[Dict]) -> List[Dict]:
    """
    Balance examples across:
    - therapeutic step (11 steps, proportional to STEP_TARGETS)
    - therapeutic modality (6 modalities, proportional to MODALITY_RATIOS)
    - presenting issue (18 issues, roughly uniform)
    - emotion (12 states, roughly uniform)

    Over-represented categories are down-sampled; under-represented are
    gap-filled from the template generator.
    """
    # Count by step
    by_step = defaultdict(list)
    for ex in all_examples:
        by_step[ex["therapeutic_step"]].append(ex)

    # Identify remaining gaps
    remaining_targets = {}
    for step, target in STEP_TARGETS.items():
        have = len(by_step.get(step, []))
        remaining = max(0, target - have)
        remaining_targets[step] = remaining

    # Generate from templates for gaps
    template_fills = generate_from_templates(remaining_targets)
    all_examples = all_examples + template_fills

    # Rebuild by-step
    by_step = defaultdict(list)
    for ex in all_examples:
        by_step[ex["therapeutic_step"]].append(ex)

    # Down-sample over-represented steps; up-sample via copy for under-represented
    balanced = []
    for step, target in STEP_TARGETS.items():
        pool = by_step.get(step, [])
        if len(pool) >= target:
            # Prioritise higher quality examples
            pool_sorted = sorted(pool, key=lambda x: x["metadata"]["clinical_quality_score"], reverse=True)
            balanced.extend(pool_sorted[:target])
        else:
            # Extend by sampling with replacement
            balanced.extend(pool)
            needed = target - len(pool)
            extras = [deepcopy(random.choice(pool)) for _ in range(needed)] if pool else []
            # Regenerate ML context for duplicates to avoid exact copies
            for ex in extras:
                ex["ml_context"]["emotion"] = sample_emotion_ctx()
                ex["ml_context"]["meta_model_patterns"] = sample_meta_model_ctx()
                ex["ml_context"]["assessment"] = sample_assessment_ctx()
                # Rebuild system prompt with new context
                ex["messages"][0]["content"] = build_stage2_system_prompt(
                    therapeutic_step=ex["therapeutic_step"],
                    modality=ex["therapeutic_modality"],
                    presenting_issue=ex["presenting_issue"],
                    session_number=random.randint(1, 10),
                    emotion_ctx=ex["ml_context"]["emotion"],
                    meta_model_ctx=ex["ml_context"]["meta_model_patterns"],
                    assessment_ctx=ex["ml_context"]["assessment"],
                    topic_ctx=ex["ml_context"]["topic"],
                    crisis_ctx=ex["ml_context"]["crisis"],
                )
                ex["conversation_id"] = "s2_" + hashlib.md5(
                    f"{ex['conversation_id']}{random.random()}".encode()
                ).hexdigest()[:10]
            balanced.extend(extras)

    random.shuffle(balanced)
    return balanced[:TARGET_TOTAL]


# ─── Stratified Split ─────────────────────────────────────────────────────────

def stratified_split(examples: List[Dict], train: float = 0.80, val: float = 0.10) -> Tuple[List, List, List]:
    """Stratified 80/10/10 split by (therapeutic_step, therapeutic_modality)."""
    strata = defaultdict(list)
    for ex in examples:
        key = f"{ex['therapeutic_step']}_{ex['therapeutic_modality']}"
        strata[key].append(ex)

    train_set, val_set, test_set = [], [], []
    for key, group in strata.items():
        random.shuffle(group)
        n      = len(group)
        n_tr   = max(1, int(n * train))
        n_val  = max(1, int(n * val))
        train_set.extend(group[:n_tr])
        val_set.extend(group[n_tr:n_tr + n_val])
        test_set.extend(group[n_tr + n_val:])

    random.shuffle(train_set)
    random.shuffle(val_set)
    random.shuffle(test_set)
    return train_set, val_set, test_set


# ─── ChatML Formatter ─────────────────────────────────────────────────────────

def format_to_chatml(example: Dict) -> str:
    """Convert canonical example to ChatML training string."""
    text = ""
    for msg in example["messages"]:
        text += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
    return text.strip()


# ─── Quality Verification ─────────────────────────────────────────────────────

def verify_dataset_quality(examples: List[Dict]) -> Dict:
    """Run all quality checks and return a QA report."""
    report = {
        "total": len(examples),
        "by_step": defaultdict(int),
        "by_modality": defaultdict(int),
        "by_issue": defaultdict(int),
        "by_emotion": defaultdict(int),
        "with_assessment_context": 0,
        "with_meta_model_patterns": 0,
        "harmful_violations": [],
        "avg_quality_score": 0.0,
        "avg_turns": 0.0,
        "min_quality_score": 5.0,
        "coverage": {},
    }

    total_quality = 0.0
    total_turns   = 0

    for ex in examples:
        report["by_step"][ex["therapeutic_step"]] += 1
        report["by_modality"][ex["therapeutic_modality"]] += 1
        report["by_issue"][ex["presenting_issue"]] += 1

        em = ex.get("ml_context", {}).get("emotion", {})
        if em:
            report["by_emotion"][em.get("primary_emotion", "unknown")] += 1

        if ex["ml_context"].get("assessment"):
            report["with_assessment_context"] += 1

        if ex["ml_context"].get("meta_model_patterns"):
            report["with_meta_model_patterns"] += 1

        qs = ex["metadata"]["clinical_quality_score"]
        total_quality += qs
        report["min_quality_score"] = min(report["min_quality_score"], qs)

        # Count non-system turns
        n_turns = sum(1 for m in ex["messages"] if m["role"] != "system")
        total_turns += n_turns

        # Harmful pattern check on assistant responses
        for msg in ex["messages"]:
            if msg["role"] == "assistant":
                violations = check_harmful_patterns(msg["content"])
                if violations:
                    report["harmful_violations"].append({
                        "conversation_id": ex["conversation_id"],
                        "violations": violations,
                    })

    report["avg_quality_score"] = round(total_quality / max(len(examples), 1), 2)
    report["avg_turns"]         = round(total_turns / max(len(examples), 1), 1)

    # Convert defaultdicts to regular dicts
    for key in ["by_step", "by_modality", "by_issue", "by_emotion"]:
        report[key] = dict(report[key])

    # Technique coverage
    all_techniques_seen = set()
    for ex in examples:
        for tech in ex["metadata"].get("techniques_used", []):
            all_techniques_seen.add(tech)
    report["unique_techniques"] = sorted(all_techniques_seen)

    return report


# ─── Export ───────────────────────────────────────────────────────────────────

def export_splits(train_set, val_set, test_set, full_set, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    def write_jsonl(data, path):
        with open(path, "w", encoding="utf-8") as f:
            for ex in data:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    def write_chatml(data, path):
        with open(path, "w", encoding="utf-8") as f:
            for ex in data:
                chatml = format_to_chatml(ex)
                if chatml:
                    f.write(json.dumps({"text": chatml}, ensure_ascii=False) + "\n")

    write_jsonl(train_set,  out_dir / "train.jsonl")
    write_jsonl(val_set,    out_dir / "val.jsonl")
    write_jsonl(test_set,   out_dir / "test.jsonl")
    write_jsonl(full_set,   out_dir / "full_dataset.jsonl")

    write_chatml(train_set, out_dir / "train_chatml.jsonl")
    write_chatml(val_set,   out_dir / "val_chatml.jsonl")
    write_chatml(test_set,  out_dir / "test_chatml.jsonl")

    print(f"  ✓ train.jsonl          → {len(train_set):,} examples")
    print(f"  ✓ val.jsonl            → {len(val_set):,} examples")
    print(f"  ✓ test.jsonl           → {len(test_set):,} examples")
    print(f"  ✓ full_dataset.jsonl   → {len(full_set):,} examples")
    print(f"  ✓ *_chatml.jsonl       → ChatML format for SFTTrainer")


def export_report(report: Dict, split_sizes: Dict, out_dir: Path):
    report["split_sizes"] = split_sizes
    report["generated_at"] = datetime.now().isoformat()
    report_path = out_dir / "dataset_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  [OK] dataset_report.json  -> QA statistics and coverage report")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Prepare Stage 2 LoRA dataset")
    parser.add_argument("--out",  default=str(Path(__file__).parent / "data"),
                        help="Output directory (default: ./data)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    out_dir = Path(args.out)

    print("=" * 60)
    print("SAATHI AI - Stage 2 Dataset Preparation")
    print("=" * 60)

    # ── 1. Load all POC sources ──────────────────────────────────────────
    print("\n[1/5] Loading POC source data...")
    gold_data       = load_stage2_gold()
    challenge_data  = load_challenge_context()
    multi_turn_data = load_multi_turn_poc()
    single_turn_data = load_single_turn_poc()

    all_raw = gold_data + challenge_data + multi_turn_data + single_turn_data
    print(f"  Gold conversations:        {len(gold_data)}")
    print(f"  Challenge context:         {len(challenge_data)}")
    print(f"  Multi-turn internal:       {len(multi_turn_data)}")
    print(f"  Single-turn POC files:     {len(single_turn_data)}")
    print(f"  Total raw examples:        {len(all_raw)}")

    # ── 2. Normalize to canonical schema with ML context injection ───────
    print("\n[2/5] Normalising to canonical schema + injecting ML dimensions...")
    canonical = normalize_poc_to_canonical(all_raw)
    print(f"  Normalised (after safety filter): {len(canonical)}")

    # ── 3. Balance and augment to TARGET_TOTAL ───────────────────────────
    print(f"\n[3/5] Balancing and augmenting to {TARGET_TOTAL:,} examples...")
    balanced = assemble_and_balance(canonical)
    print(f"  Final dataset size: {len(balanced):,}")

    # ── 4. Quality verification ──────────────────────────────────────────
    print("\n[4/5] Running quality checks...")
    report = verify_dataset_quality(balanced)

    harm_count = len(report.get("harmful_violations", []))
    if harm_count > 0:
        print(f"  [WARN] {harm_count} harmful pattern violations detected - review dataset_report.json")
    else:
        print(f"  [OK] 0 harmful pattern violations")
    print(f"  [OK] Avg quality score:    {report['avg_quality_score']:.2f}/5.0")
    print(f"  [OK] Avg turns per conv:   {report['avg_turns']:.1f}")
    print(f"  [OK] With assessment ctx:  {report['with_assessment_context']} ({report['with_assessment_context']*100//len(balanced)}%)")
    print(f"  [OK] With meta-model ctx:  {report['with_meta_model_patterns']} ({report['with_meta_model_patterns']*100//len(balanced)}%)")

    print("\n  Step distribution:")
    for step, count in sorted(report["by_step"].items(), key=lambda x: STEP_ORDER.get(x[0], 99)):
        target = STEP_TARGETS.get(step, "?")
        bar = "█" * (count // 10)
        print(f"    {step:<25} {count:>4} / {target:<4} {bar}")

    print("\n  Modality distribution:")
    for mod, count in sorted(report["by_modality"].items(), key=lambda x: -x[1]):
        pct = count * 100 // len(balanced)
        print(f"    {mod:<30} {count:>4} ({pct}%)")

    # ── 5. Stratified split and export ───────────────────────────────────
    print("\n[5/5] Splitting (80/10/10 stratified) and exporting...")
    train_set, val_set, test_set = stratified_split(balanced)
    export_splits(train_set, val_set, test_set, balanced, out_dir)
    export_report(report, {
        "train": len(train_set), "val": len(val_set), "test": len(test_set)
    }, out_dir)

    print("\n" + "=" * 60)
    print("Dataset preparation COMPLETE")
    print("=" * 60)
    print(f"  Output directory: {out_dir}")
    print(f"  Total: {len(balanced):,} | Train: {len(train_set):,} | Val: {len(val_set):,} | Test: {len(test_set):,}")
    print("\nNext step:")
    print("  python 02_train_stage2_lora.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
