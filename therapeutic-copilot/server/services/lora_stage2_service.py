"""
SAATHI AI — Stage 2 LoRA Inference Service
==========================================
Manages Stage 2 (therapeutic co-pilot) inference using the locally trained
Qwen2.5-3B-Instruct + r=16 LoRA adapter (hosted entirely on local GPU).

2-Tier Fallback:
  1. Local LoRA adapter (GPU — loaded from ml_models/stage2_therapy_model/)
  2. Structured mock responses per therapeutic step (demo / pre-training mode)

The system prompt is built with ALL ML model dimension features injected:
  - Therapeutic step (1–11 of 11-step clinical protocol)
  - Emotion classifier output (primary, intensity, secondary)
  - Meta-model pattern detector output (NLP cognitive patterns)
  - Assessment context (PHQ-9, GAD-7, etc. where available)
  - Topic classifier output
  - Crisis state
"""

import os
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from loguru import logger
from config import settings

# ─── Default adapter path ─────────────────────────────────────────────────────
DEFAULT_ADAPTER_PATH = Path(__file__).parent.parent / "ml_models" / "stage2_therapy_model"

# ─── Therapeutic Step Definitions ─────────────────────────────────────────────

STEP_NAMES = [
    "check_in", "session_goal", "exploration", "validation",
    "psychoeducation", "cbt_intervention", "mindfulness_grounding",
    "skill_building", "practice_homework", "summary", "closing",
]
STEP_ORDER = {name: i + 1 for i, name in enumerate(STEP_NAMES)}

STEP_INSTRUCTIONS = {
    "check_in": (
        "Gently check in on how the user has been since the last interaction. "
        "Ask ONE warm, open-ended question. Do not rush to problem-solving."
    ),
    "session_goal": (
        "Collaboratively set a focus for this session. Ask what they'd like to work on. "
        "Reflect back their stated goal. If multiple issues, help them choose ONE."
    ),
    "exploration": (
        "Open-ended exploration of the presenting issue. "
        "Use: 'Tell me more about...', 'What's that like for you?' "
        "Follow the thread — do NOT offer solutions yet."
    ),
    "validation": (
        "Deep validation of the user's emotional experience. "
        "Reflect, name the emotion, communicate it makes sense. "
        "NO advice, NO silver linings, NO 'at least...' Use: 'It sounds like...', 'I hear...'"
    ),
    "psychoeducation": (
        "Explain the psychological mechanism behind what they are experiencing. "
        "Connect to a known concept. Normalize. Use accessible language. "
        "Invite their reaction: 'Does that resonate with you?'"
    ),
    "cbt_intervention": (
        "Apply one CBT technique: Thought Record, Cognitive Restructuring, "
        "Socratic Questioning, or Behavioral Activation. "
        "Introduce gently. Guide step by step. Stay curious, not prescriptive."
    ),
    "mindfulness_grounding": (
        "Guide a mindfulness or grounding exercise. Ask permission first. "
        "Available: 5-4-3-2-1, breath awareness, body scan, RAIN, urge surfing. "
        "Guide slowly. End with: 'How are you feeling compared to when we started?'"
    ),
    "skill_building": (
        "Teach a concrete, practical coping skill matched to the issue and modality. "
        "Step by step. Check comprehension. Connect to their specific situation."
    ),
    "practice_homework": (
        "Assign specific, achievable between-session practice. "
        "Use implementation intention: 'When X happens, I will do Y'. "
        "Anticipate the obstacle. Frame as experiment. Check willingness."
    ),
    "summary": (
        "Summarise ONE key insight from this session using the user's own words. "
        "Reflect any progress. Keep it brief. Bridge to next session."
    ),
    "closing": (
        "Warm, affirming close. Acknowledge the user's effort. "
        "Confirm homework and next steps. End with genuine warmth."
    ),
}

TOPIC_GUIDANCE = {
    "workplace_stress":      "Acknowledge occupational pressure directly. Validate systemic factors.",
    "financial_stress":      "Be sensitive about costs in any discussion of resources.",
    "grief_bereavement":     "Slow the pace. Presence and normalisation over technique.",
    "trauma_related":        "TRAUMA ACTIVE: use trauma-informed approach. No standard CBT.",
    "relationship_issues":   "Be warm and non-judgmental. Avoid taking sides.",
    "academic_pressure":     "Normalise performance anxiety. Validate the pressure explicitly.",
    "social_anxiety":        "Small steps only. No overwhelming exposure tasks early.",
    "substance_use_ambivalence": "Motivational Interviewing ONLY. No directives.",
}

HARMFUL_PATTERNS = [
    re.compile(r"\byou should (leave|divorce|quit|stop)\b", re.IGNORECASE),
    re.compile(r"\bthat'?s? (stupid|wrong|irrational)\b",  re.IGNORECASE),
    re.compile(r"\bi (know|understand) exactly how you feel\b", re.IGNORECASE),
    re.compile(r"\bthings will definitely get better\b",    re.IGNORECASE),
    re.compile(r"\bother people have it worse\b",           re.IGNORECASE),
    re.compile(r"\bjust (cheer up|calm down|snap out of it)\b", re.IGNORECASE),
]


# ─── System Prompt Builder ────────────────────────────────────────────────────

def build_stage2_system_prompt(
    therapeutic_step: str,
    session_number: int,
    presenting_issue: str,
    emotion_result: Optional[Dict],
    meta_model_result: Optional[Dict],
    assessment_context: Optional[Dict],
    topic_result: Optional[Dict],
    crisis_context: Optional[Dict],
) -> str:
    """
    Build the complete Stage 2 system prompt with ALL ML dimension blocks
    injected in the same format used during training.
    """
    step_num   = STEP_ORDER.get(therapeutic_step, 1)
    step_instr = STEP_INSTRUCTIONS.get(therapeutic_step, "Guide the conversation therapeutically.")
    issue_label = presenting_issue.replace("_", " ").title() if presenting_issue else "General"

    prompt = f"""You are Saathi, an evidence-based AI therapeutic co-pilot supporting users who have already booked therapy sessions.

Your therapeutic foundation:
• CBT  • DBT  • Mindfulness  • ACT  • Motivational Interviewing

Core Principles:
• Empathy before technique — always validate before intervening
• ONE question at a time — never multiple questions in one message
• Follow the user's pace — never rush
• Clinical safety is non-negotiable
• Sound human, warm, genuine — not clinical or scripted

## Therapeutic Step: {step_num}/11 — {therapeutic_step.replace('_', ' ').title()}
{step_instr}

## Session: {session_number} | Presenting Issue: {issue_label}"""

    # ── Emotion Block ─────────────────────────────────────────────────────────
    if emotion_result:
        em   = emotion_result.get("primary_emotion", "neutral")
        intn = emotion_result.get("intensity", 0.5)
        sec  = emotion_result.get("secondary_emotion")
        hihl = emotion_result.get("high_intensity_hopelessness", False)

        prompt += f"\n\n## Emotional State\nDetected: {em} (intensity: {intn:.0%})"
        if sec:
            prompt += f" | Secondary: {sec}"

        if hihl or (em in ("hopelessness", "despair") and intn > 0.70):
            prompt += "\n→ HIGH DISTRESS: Pause technique. Prioritise safety and containment first."
        elif em in ("anxiety", "fear") and intn > 0.70:
            prompt += "\n→ High anxiety: validate before any cognitive work. Consider grounding."
        elif em in ("shame", "guilt") and intn > 0.55:
            prompt += "\n→ Shame present: avoid language that implies fault or personal weakness."
        elif em in ("grief", "sadness") and intn > 0.65:
            prompt += "\n→ Deep sadness/grief: slow down, presence before technique."

    # ── Meta-Model / Cognitive Pattern Block ─────────────────────────────────
    patterns = []
    if meta_model_result:
        if isinstance(meta_model_result, dict):
            patterns = meta_model_result.get("patterns_detected", [])
        elif isinstance(meta_model_result, list):
            patterns = meta_model_result

    if patterns:
        prompt += "\n\n## Cognitive Patterns Detected"
        for p in patterns[:3]:
            ptype = p.get("pattern_subtype", p.get("pattern_type", "unknown"))
            text  = p.get("matched_text", "")
            conf  = p.get("confidence", 0.75)
            rq    = p.get("recovery_question", p.get("recovery_questions", [""])[0] if p.get("recovery_questions") else "")
            prompt += f"\n- {ptype.replace('_', ' ').title()}: \"{text}\" ({conf:.0%})"
            if rq:
                prompt += f"\n  → Recovery: {rq}"
        prompt += "\n→ Use recovery questions to gently challenge these patterns."

    # ── Assessment Context Block ───────────────────────────────────────────────
    if assessment_context:
        days = assessment_context.get("days_ago", assessment_context.get("assessment_date_days_ago", 0))
        prompt += f"\n\n## Assessment Context ({days} day{'s' if days != 1 else ''} ago)"

        for key, label, max_score in [
            ("phq9", "PHQ-9", 27), ("gad7", "GAD-7", 21),
            ("pss",  "PSS-10", 40), ("isi", "ISI", 28),
            ("pcl5", "PCL-5", 80), ("spin", "SPIN", 68),
        ]:
            if key in assessment_context:
                sev = assessment_context.get(f"{key}_sev", assessment_context.get(f"{key}_severity", ""))
                sev_label = sev.replace("_", " ").title() if sev else ""
                prompt += f"\n{label}: {assessment_context[key]}/{max_score}"
                if sev_label:
                    prompt += f" — {sev_label}"

        phq = assessment_context.get("phq9", 0)
        gad = assessment_context.get("gad7", 0)
        if phq >= 20 or gad >= 15:
            prompt += "\n→ Severe symptoms: confirm therapist is actively involved."
        elif phq >= 10 or gad >= 10:
            prompt += "\n→ Moderate symptoms: watch for avoidance and comorbid presentation."

    # ── Topic Block ───────────────────────────────────────────────────────────
    if topic_result:
        topic = topic_result.get("primary_topic", presenting_issue) or presenting_issue
        guidance = TOPIC_GUIDANCE.get(topic, "")
        prompt += f"\n\n## Topic: {topic.replace('_', ' ').title()}"
        if guidance:
            prompt += f"\n→ {guidance}"

    # ── Crisis Block ──────────────────────────────────────────────────────────
    crisis_active = False
    if crisis_context:
        score = crisis_context.get("severity_score", crisis_context.get("severity", 0.0))
        crisis_active = crisis_context.get("crisis_active", False) or score >= 7

    if crisis_active:
        prompt += (
            "\n\n## ⚠ CRISIS STATE ACTIVE\n"
            "STOP all therapy. Do NOT apply any technique.\n"
            "Validate → ask directly about safety → provide resources.\n"
            "iCall: +91-9152987821 | Vandrevala: 1860-2662-345 | NIMHANS: 080-46110007"
        )
    else:
        prompt += "\n\n## Crisis State: None detected"

    return prompt.strip()


# ─── Step Progression Logic ───────────────────────────────────────────────────

def determine_therapeutic_step(current_step_number: int) -> str:
    """Map session step counter (0–10) to therapeutic step name."""
    idx = max(0, min(current_step_number, len(STEP_NAMES) - 1))
    return STEP_NAMES[idx]


def should_advance_step(
    current_step: str,
    turns_in_step: int,
    emotion_result: Optional[Dict],
) -> bool:
    """
    Basic heuristic for step advancement.
    Can be overridden by the clinician dashboard.
    """
    min_turns = {
        "check_in": 1, "session_goal": 1, "exploration": 2,
        "validation": 2, "psychoeducation": 1, "cbt_intervention": 3,
        "mindfulness_grounding": 2, "skill_building": 2,
        "practice_homework": 1, "summary": 1, "closing": 1,
    }
    min_req = min_turns.get(current_step, 2)
    if turns_in_step < min_req:
        return False

    # If user is very distressed, hold at validation longer
    if emotion_result:
        intensity = emotion_result.get("intensity", 0.5)
        hihl = emotion_result.get("high_intensity_hopelessness", False)
        if (hihl or intensity > 0.85) and current_step in ("check_in", "exploration", "validation"):
            return False

    return True


# ─── Stage 2 Service ──────────────────────────────────────────────────────────

class Stage2LoRAService:
    """
    Manages Stage 2 LoRA inference.

    Load order:
      1. LoRA adapter from STAGE2_LORA_ADAPTER_PATH (or default path)
      2. Together AI API fallback
      3. Structured mock responses (demo mode)
    """

    _instance: Optional["Stage2LoRAService"] = None

    def __new__(cls) -> "Stage2LoRAService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._model       = None
        self._tokenizer   = None
        self._model_config = {}
        self.is_ready     = False
        self.backend      = "none"
        self._initialized = True
        self._setup()

    def _setup(self):
        adapter_path = Path(
            getattr(settings, "STAGE2_LORA_ADAPTER_PATH", "") or DEFAULT_ADAPTER_PATH
        )

        if adapter_path.exists() and (adapter_path / "adapter_config.json").exists():
            try:
                self._load_lora(adapter_path)
                self.backend  = "lora"
                self.is_ready = True
                logger.info(f"Stage2LoRAService: Loaded adapter from {adapter_path}")
            except Exception as exc:
                logger.warning(f"Stage2LoRAService: LoRA load failed ({exc}). Falling back.")
        else:
            logger.warning(
                f"Stage2LoRAService: Adapter not at {adapter_path}. "
                "Run fine_tune/stage2/04_deploy_stage2_adapter.py after training."
            )

        if not self.is_ready:
            self.backend  = "mock"
            self.is_ready = True
            logger.warning(
                "Stage2LoRAService: Adapter not loaded — using mock responses. "
                "Run fine_tune/stage2/ pipeline to train and deploy the local model."
            )

    def _load_lora(self, adapter_path: Path):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        from peft import PeftModel

        cfg_file = adapter_path / "model_config.json"
        if cfg_file.exists():
            with open(cfg_file) as f:
                self._model_config = json.load(f)

        adapter_cfg_file = adapter_path / "adapter_config.json"
        with open(adapter_cfg_file) as f:
            adapter_cfg = json.load(f)
        base_model = adapter_cfg.get("base_model_name_or_path", "Qwen/Qwen2.5-7B-Instruct")

        logger.info(f"Loading base model: {base_model}")
        bnb = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True,
        )
        self._tokenizer = AutoTokenizer.from_pretrained(str(adapter_path), trust_remote_code=True)
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        base = AutoModelForCausalLM.from_pretrained(
            base_model, quantization_config=bnb, device_map="auto",
            trust_remote_code=True, torch_dtype=torch.float16,
        )
        self._model  = PeftModel.from_pretrained(base, str(adapter_path))
        self._model.eval()
        self._device = next(self._model.parameters()).device

    def _format_chatml(self, messages: List[Dict]) -> str:
        text = ""
        for msg in messages:
            text += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
        text += "<|im_start|>assistant\n"
        return text

    def _generate_local(self, messages: List[Dict], max_new_tokens: int = 400) -> str:
        import torch
        prompt  = self._format_chatml(messages)
        inputs  = self._tokenizer(prompt, return_tensors="pt").to(self._device)
        cfg     = self._model_config.get("service_config", self._model_config)

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=cfg.get("temperature", 0.75),
                top_p=cfg.get("top_p", 0.90),
                top_k=cfg.get("top_k", 40),
                repetition_penalty=cfg.get("repetition_penalty", 1.15),
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        gen_ids = outputs[0][inputs["input_ids"].shape[1]:]
        return self._tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

    def _check_safety(self, response: str) -> Tuple[bool, List[str]]:
        """Return (is_safe, violations_list)."""
        violations = []
        for pat in HARMFUL_PATTERNS:
            if pat.search(response):
                violations.append(pat.pattern)
        return len(violations) == 0, violations

    def _safe_fallback(self, step: str, emotion_result: Optional[Dict] = None) -> str:
        em = emotion_result.get("primary_emotion", "difficult") if emotion_result else "difficult"
        return (
            f"I hear that you're carrying something {em} right now. "
            f"I'm here with you. Can you tell me a little more about what you're experiencing?"
        )

    def _mock_response(self, step: str, session_number: int) -> str:
        mocks = {
            "check_in":              "Welcome back. How have you been since we last spoke? What stands out from the past week?",
            "session_goal":          "I'm glad you're here. What would feel most valuable to focus on together today?",
            "exploration":           "That sounds like it's been weighing on you. Can you tell me more about what that's like day to day?",
            "validation":            "What you're describing makes complete sense. Carrying that while keeping everything else going is genuinely hard. I hear you.",
            "psychoeducation":       "What you're experiencing is a very well-understood response. When the nervous system is under sustained pressure, it does exactly this. You're not broken — you're responding to a real load.",
            "cbt_intervention":      "I'd like to try something with you — a technique called a thought record. It's one of the most practical CBT tools for exactly what you're describing. Would you be open to exploring it together?",
            "mindfulness_grounding": "I'd like to guide you through a brief grounding exercise — just three minutes. Would you be willing to try? Keep your eyes open and stay where you are.",
            "skill_building":        "Let me teach you a concrete skill you can use between our sessions. It's simple, but research shows it works reliably when practiced consistently.",
            "practice_homework":     "For this week: let's make the homework specific. When exactly in your day would you do this? And what might get in the way?",
            "summary":               "You've done real work today. The key thing you found: the thought was carrying far more weight than the evidence warranted. That's an important shift.",
            "closing":               "You showed up today and did something genuinely hard. That matters. Take the homework into the week — and know I'll be here when you return.",
        }
        return mocks.get(step, "I'm here with you. What would be most helpful to focus on right now?")

    async def generate(
        self,
        conversation_history: List[Dict],
        current_step: int = 0,
        presenting_issue: str = "general",
        session_number: int = 1,
        emotion_result: Optional[Dict] = None,
        meta_model_result: Optional[Dict] = None,
        assessment_context: Optional[Dict] = None,
        topic_result: Optional[Dict] = None,
        crisis_context: Optional[Dict] = None,
        max_new_tokens: int = 400,
    ) -> Dict:
        """
        Generate Stage 2 therapeutic response.

        Args:
            conversation_history: list of {role, content} WITHOUT system message
            current_step: 0-10 (maps to 11 therapeutic steps)
            presenting_issue: primary clinical concern (string)
            session_number: which session this is (1-N)
            emotion_result: from EmotionClassifierService (dict or dataclass-like)
            meta_model_result: from MetaModelDetectorService
            assessment_context: PHQ-9, GAD-7, etc. scores dict
            topic_result: from TopicClassifierService
            crisis_context: from CrisisDetectionService
            max_new_tokens: max tokens to generate

        Returns dict with: response, therapeutic_step, session_number,
            techniques_suggested, crisis_detected, safety_check_passed,
            backend, latency_ms
        """
        start = time.time()
        therapeutic_step = determine_therapeutic_step(current_step)

        system_prompt = build_stage2_system_prompt(
            therapeutic_step=therapeutic_step,
            session_number=session_number,
            presenting_issue=presenting_issue,
            emotion_result=emotion_result,
            meta_model_result=meta_model_result,
            assessment_context=assessment_context,
            topic_result=topic_result,
            crisis_context=crisis_context,
        )

        messages = [{"role": "system", "content": system_prompt}] + conversation_history

        try:
            if self.backend == "lora":
                response = self._generate_local(messages, max_new_tokens)
            else:
                response = self._mock_response(therapeutic_step, session_number)
        except Exception as exc:
            logger.error(f"Stage2 generation failed ({self.backend}): {exc}")
            response = self._safe_fallback(therapeutic_step, emotion_result)

        # Post-generation safety check
        is_safe, violations = self._check_safety(response)
        if not is_safe:
            logger.warning(f"Stage2: harmful pattern in response — {violations}. Using safe fallback.")
            response = self._safe_fallback(therapeutic_step, emotion_result)

        # Detect crisis signal in response (model should have escalated)
        resp_lower = response.lower()
        crisis_in_response = any(
            kw in resp_lower for kw in ["icall", "vandrevala", "1860", "9152", "nimhans", "crisis resources"]
        )

        # Infer techniques mentioned
        techniques_suggested = []
        technique_map = {
            "thought record":        "thought_record",
            "cognitive restructuring": "cognitive_restructuring",
            "socratic":              "socratic_questioning",
            "behavioral activation": "behavioral_activation",
            "5-4-3-2-1":            "grounding_5431",
            "tipp":                  "DBT_TIPP",
            "dear man":              "DBT_DEAR_MAN",
            "radical acceptance":    "radical_acceptance",
            "values":                "values_clarification",
            "defusion":              "cognitive_defusion",
            "body scan":             "body_scan",
        }
        for phrase, technique in technique_map.items():
            if phrase in resp_lower:
                techniques_suggested.append(technique)

        latency_ms = round((time.time() - start) * 1000)

        return {
            "response":               response,
            "therapeutic_step":       therapeutic_step,
            "step_number":            current_step + 1,
            "session_number":         session_number,
            "techniques_suggested":   techniques_suggested,
            "crisis_detected":        crisis_in_response,
            "safety_check_passed":    is_safe,
            "backend":                self.backend,
            "latency_ms":             latency_ms,
        }


# ─── Singleton accessor ────────────────────────────────────────────────────────

_service_instance: Optional[Stage2LoRAService] = None


def get_stage2_service() -> Stage2LoRAService:
    global _service_instance
    if _service_instance is None:
        _service_instance = Stage2LoRAService()
    return _service_instance
