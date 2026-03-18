"""
SAATHI AI — Stage 1 LoRA Inference Service
==========================================
Loads the trained Qwen2.5-7B-Instruct + LoRA r=8 adapter for
Stage 1 lead generation conversations.

Features:
  - Singleton model loading (loaded once at startup)
  - 4-bit QLoRA inference
  - Lead score calculation
  - Stage-aware system prompt builder
  - Graceful fallback to Together AI if weights not present

Usage:
    from services.lora_stage1_service import get_stage1_service
    svc = get_stage1_service()
    result = await svc.generate(conversation_history, company_name, turn_number)
"""

import os
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from loguru import logger

from config import settings

# ─── Default adapter path (set STAGE1_LORA_ADAPTER_PATH in .env to override) ──

DEFAULT_ADAPTER_PATH = Path(__file__).parent.parent / "ml_models" / "stage1_sales_model"


# ─── Stage system prompts ──────────────────────────────────────────────────────

STAGE_INSTRUCTIONS = {
    1: "Focus on a warm welcome. Express genuine curiosity. Ask one open question about what brought them here.",
    2: "Build rapport. Reflect back what they've shared. Make them feel heard and understood.",
    3: "Explore their situation deeply. Use open-ended questions. Surface the real pain point — be patient.",
    4: "Connect what they've shared to the value of the service. Use their own words and feelings.",
    5: "Gently introduce therapy as a path forward. Normalise help-seeking. Don't pressure.",
    6: "Build trust and credibility. Mention specific therapist specialisations and platform quality.",
    7: "Handle any objections with empathy. Validate their concern before reframing.",
    8: "Warm, natural transition to booking. Make it easy. Ask for their preferences.",
}

TOPIC_CONTEXT_MAP = {
    "workplace_stress":  "They are dealing with work-related stress. Acknowledge workplace pressures specifically.",
    "relationship_issues": "Relationship challenges are present. Be especially warm and non-judgmental.",
    "academic_stress":   "Academic pressure is their primary concern. Normalise performance anxiety.",
    "health_concerns":   "Health-related anxiety is present. Validate the mind-body connection.",
    "financial_stress":  "Financial stress is present. Be sensitive in any discussion about costs.",
    "grief":             "Grief or loss is present. Slow down. Prioritise presence over solutions.",
    "trauma":            "Trauma signals present. Do NOT continue sales flow. Prioritise safety and referral.",
}


def build_stage1_system_prompt(
    company_name: str,
    conversation_stage: int,
    lead_score: float = 0.0,
    emotion_result: Optional[Dict] = None,
    topic_result: Optional[Dict] = None,
    intent_result: Optional[Dict] = None,
) -> str:
    """
    Build the complete Stage 1 system prompt.

    The LoRA model already knows the conversation patterns from training;
    this prompt provides real-time context (stage, emotion, topic, lead score).
    """
    stage_instruction = STAGE_INSTRUCTIONS.get(conversation_stage, STAGE_INSTRUCTIONS[3])

    emotion_note = ""
    if emotion_result:
        primary = emotion_result.get("primary_emotion", "neutral")
        intensity = emotion_result.get("intensity", 0.5)
        if primary in ("anxiety", "sadness", "fear") and intensity > 0.6:
            emotion_note = (
                f"\nNote: User shows {primary} (intensity {intensity:.0%}). "
                "Be extra warm. Slow down. Validate before any suggestion."
            )
        elif primary in ("hopelessness", "despair") and intensity > 0.65:
            emotion_note = (
                "\n⚠ High distress detected. PAUSE sales flow immediately. "
                "Prioritise emotional safety. Ask directly about wellbeing."
            )

    topic_note = ""
    if topic_result and topic_result.get("primary_topic"):
        topic = topic_result["primary_topic"]
        topic_note = f"\nTopic context: {TOPIC_CONTEXT_MAP.get(topic, '')}"

    booking_guidance = (
        "→ Ready to guide toward booking"
        if lead_score > 70
        else "→ Still building rapport and trust"
    )

    prompt = f"""You are Saathi, a warm and empathetic wellness guide for {company_name}'s employee wellness program.

## Your Role
You are having an initial conversation with a {company_name} employee. Your goal is to build genuine trust, understand their situation, and gently guide them toward their first therapy session — but NEVER at the cost of their wellbeing or honesty.

## Current Conversation Stage: {conversation_stage}/8
{stage_instruction}

## Conversation Guidelines
- Be warm and human — not corporate or scripted
- Ask ONE question at a time — never multiple questions in one message
- Keep responses to 2–4 sentences maximum
- Never use pressure tactics, urgency language, or false scarcity
- If any crisis signals appear, IMMEDIATELY shift to support mode and provide crisis resources
- Use the user's name if known
- Acknowledge emotions before offering solutions

## Lead Score: {lead_score:.0f}/100
{booking_guidance}
{emotion_note}
{topic_note}"""

    return prompt.strip()


# ─── Lead Score Calculator ─────────────────────────────────────────────────────

def calculate_lead_score(conversation_history: List[Dict], latest_response: str) -> Tuple[float, Dict]:
    """
    Calculate lead score (0–100) based on conversation signals.

    Factors:
      - Engagement level: message length and quality (0–30)
      - Pain point disclosed: user shared a real problem (0–20)
      - Positive response: responded positively to therapy idea (0–20)
      - Booking intent signal: asked about booking/availability (0–15)
      - Objection resolved: had objection that was resolved (0–15)
    """
    user_messages = [m for m in conversation_history if m.get("role") == "user"]
    all_text = " ".join(m.get("content", "") for m in user_messages).lower()

    # Engagement level (0–30): based on average message length
    if user_messages:
        avg_len = sum(len(m.get("content", "")) for m in user_messages) / len(user_messages)
        engagement = min(30, avg_len / 5)
    else:
        engagement = 0

    # Pain point disclosed (0–20)
    pain_keywords = [
        "stress", "anxious", "anxiety", "depressed", "burnout", "struggling",
        "overwhelm", "can't cope", "exhausted", "panic", "sad", "hopeless",
        "family", "relationship", "work is", "marriage", "divorce",
    ]
    pain_disclosed = 20 if any(kw in all_text for kw in pain_keywords) else 0

    # Positive response to therapy (0–20)
    positive_keywords = [
        "maybe", "i suppose", "that makes sense", "okay", "i see", "interesting",
        "sounds good", "worth trying", "open to", "yes", "alright", "sure",
        "i'd like", "i want", "would like",
    ]
    positive_response = 20 if any(kw in all_text for kw in positive_keywords) else 0

    # Booking intent signal (0–15)
    booking_keywords = [
        "how do i book", "book a session", "schedule", "available",
        "appointment", "when can", "tomorrow", "next week",
    ]
    booking_intent = 15 if any(kw in all_text for kw in booking_keywords) else 0

    # Objection handled (0–15): user raised concern but continued engaging
    objection_keywords = [
        "but", "however", "i'm not sure", "don't know", "worried",
        "concern", "expensive", "time", "skeptical", "not sure",
    ]
    had_objection = any(kw in all_text for kw in objection_keywords)
    continued_engaging = len(user_messages) >= 3
    objection_resolved = 15 if (had_objection and continued_engaging) else 0

    total = engagement + pain_disclosed + positive_response + booking_intent + objection_resolved

    factors = {
        "engagement_level": round(engagement, 1),
        "pain_point_disclosed": pain_disclosed,
        "positive_response": positive_response,
        "booking_intent_signal": booking_intent,
        "objection_resolved": objection_resolved,
    }

    return min(100, round(total, 1)), factors


# ─── Stage 1 Service ───────────────────────────────────────────────────────────

class Stage1LoRAService:
    """
    Manages Stage 1 LoRA inference.

    Load order:
      1. Try to load LoRA adapter from STAGE1_LORA_ADAPTER_PATH
      2. If weights not found, fall back to Together AI API
      3. If Together AI not configured, return structured mock response
    """

    _instance: Optional["Stage1LoRAService"] = None

    def __new__(cls) -> "Stage1LoRAService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._model = None
        self._tokenizer = None
        self._model_config = {}
        self.is_ready = False
        self.backend = "none"
        self._initialized = True
        self._setup()

    def _setup(self):
        """Try to load LoRA model; fall back gracefully."""
        adapter_path = Path(
            getattr(settings, "STAGE1_LORA_ADAPTER_PATH", "") or DEFAULT_ADAPTER_PATH
        )

        if adapter_path.exists() and (adapter_path / "adapter_config.json").exists():
            try:
                self._load_lora(adapter_path)
                self.backend = "lora"
                self.is_ready = True
                logger.info(f"Stage1LoRAService: Loaded LoRA adapter from {adapter_path}")
            except Exception as exc:
                logger.warning(f"Stage1LoRAService: LoRA load failed ({exc}). Falling back.")
        else:
            logger.warning(
                f"Stage1LoRAService: Adapter not found at {adapter_path}. "
                "Falling back to Together AI. "
                "Run fine_tune/stage1/04_deploy_adapter.py after training."
            )

        if not self.is_ready:
            if settings.TOGETHER_API_KEY:
                self.backend = "together_ai"
                self.is_ready = True
                logger.info("Stage1LoRAService: Using Together AI fallback.")
            else:
                self.backend = "mock"
                self.is_ready = True
                logger.warning("Stage1LoRAService: No model or API — using mock responses.")

    def _load_lora(self, adapter_path: Path):
        """Load Qwen + LoRA adapter using 4-bit QLoRA."""
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        from peft import PeftModel

        # Read model config
        config_file = adapter_path / "model_config.json"
        if config_file.exists():
            with open(config_file) as f:
                self._model_config = json.load(f)

        adapter_cfg_file = adapter_path / "adapter_config.json"
        with open(adapter_cfg_file) as f:
            adapter_cfg = json.load(f)

        base_model = adapter_cfg.get("base_model_name_or_path", "Qwen/Qwen2.5-7B-Instruct")

        logger.info(f"Loading base model: {base_model}")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

        self._tokenizer = AutoTokenizer.from_pretrained(
            str(adapter_path), trust_remote_code=True
        )
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        base = AutoModelForCausalLM.from_pretrained(
            base_model,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16,
        )
        self._model = PeftModel.from_pretrained(base, str(adapter_path))
        self._model.eval()
        self._device = next(self._model.parameters()).device

    def _format_chatml(self, messages: List[Dict]) -> str:
        text = ""
        for msg in messages:
            text += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
        text += "<|im_start|>assistant\n"
        return text

    def _generate_local(self, messages: List[Dict], max_new_tokens: int = 300) -> str:
        """Generate using local LoRA model."""
        import torch
        prompt = self._format_chatml(messages)
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)

        cfg = self._model_config.get("service_config", {})
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=cfg.get("temperature", 0.8),
                top_p=cfg.get("top_p", 0.92),
                top_k=cfg.get("top_k", 50),
                repetition_penalty=cfg.get("repetition_penalty", 1.1),
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        return self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

    async def _generate_together(self, messages: List[Dict], max_new_tokens: int = 300) -> str:
        """Fall back to Together AI inference."""
        import httpx
        payload = {
            "model": settings.TOGETHER_MODEL,
            "messages": messages,
            "max_tokens": max_new_tokens,
            "temperature": 0.8,
            "top_p": 0.92,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.TOGETHER_API_KEY}"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def generate(
        self,
        conversation_history: List[Dict],
        company_name: str = "your company",
        turn_number: int = 1,
        emotion_result: Optional[Dict] = None,
        topic_result: Optional[Dict] = None,
        intent_result: Optional[Dict] = None,
        max_new_tokens: int = 300,
    ) -> Dict:
        """
        Generate Stage 1 response with lead scoring.

        Args:
            conversation_history: list of {role, content} dicts (NO system prompt)
            company_name: tenant company name for system prompt
            turn_number: current turn (1-8)
            emotion_result: from EmotionClassifierService
            topic_result: from TopicClassifierService
            intent_result: from IntentClassifierService
            max_new_tokens: max tokens to generate

        Returns:
            {
                response: str,
                stage: "lead_generation",
                turn_number: int,
                lead_score: float,
                lead_factors: dict,
                booking_intent_detected: bool,
                crisis_detected: bool,
                backend: str,
                latency_ms: int,
            }
        """
        start = time.time()

        # Build lead score BEFORE generating (based on current history)
        lead_score, lead_factors = calculate_lead_score(conversation_history, "")

        # Determine conversation stage (1-8) from turn count
        conversation_stage = min(8, max(1, turn_number))

        # Build system prompt
        system_prompt = build_stage1_system_prompt(
            company_name=company_name,
            conversation_stage=conversation_stage,
            lead_score=lead_score,
            emotion_result=emotion_result,
            topic_result=topic_result,
            intent_result=intent_result,
        )

        # Assemble full messages
        messages = [{"role": "system", "content": system_prompt}] + conversation_history

        # Generate
        try:
            if self.backend == "lora":
                response = self._generate_local(messages, max_new_tokens)
            elif self.backend == "together_ai":
                response = await self._generate_together(messages, max_new_tokens)
            else:
                response = self._mock_response(conversation_stage, company_name)
        except Exception as exc:
            logger.error(f"Stage1 generation failed ({self.backend}): {exc}")
            response = (
                "I'm here to support you. Could you tell me a little more about what's brought you here today?"
            )

        # Detect intents in response
        resp_lower = response.lower()
        booking_intent = any(
            kw in resp_lower for kw in
            ["book", "schedule", "appointment", "slot", "session this week", "available"]
        )
        crisis_detected = any(
            kw in resp_lower for kw in
            ["icall", "vandrevala", "1860", "9152", "crisis", "emergency services"]
        )

        latency_ms = round((time.time() - start) * 1000)

        return {
            "response": response,
            "stage": "lead_generation",
            "stage_order": conversation_stage,
            "turn_number": turn_number,
            "lead_score": lead_score,
            "lead_factors": lead_factors,
            "booking_intent_detected": booking_intent,
            "crisis_detected": crisis_detected,
            "backend": self.backend,
            "latency_ms": latency_ms,
        }

    def _mock_response(self, stage: int, company_name: str) -> str:
        """Structured mock response for demo/testing without GPU."""
        mock_responses = {
            1: f"Hi! I'm so glad you've reached out. I'm Saathi, your wellness companion here at {company_name}. Everything you share is completely confidential. How are you feeling today, honestly?",
            2: "I hear you. It sounds like things have been quite challenging lately. Can you tell me a bit more about what's been going on?",
            3: "That sounds really difficult to carry. How long have you been feeling this way — and is it affecting your sleep or relationships at home as well?",
            4: "What you've shared tells me that this is genuinely weighing on you. The good news is that what you're describing is something we support people with every day.",
            5: "Many people in exactly your position have found real relief through speaking with a therapist. It's not about being in crisis — it's about giving yourself the support you deserve.",
            6: "Our therapists are licensed, experienced, and many specialise specifically in workplace stress and the kind of pressure you've described. Your sessions are fully confidential.",
            7: "That's a completely understandable concern. What I can tell you is that your employer doesn't see individual session details — only anonymised aggregate data.",
            8: "Based on what you've shared, I'd love to connect you with one of our therapists. Would you prefer morning, afternoon, or evening slots? And do you have a preference for the gender of your therapist?",
        }
        return mock_responses.get(stage, mock_responses[3])


# ─── Singleton accessor ────────────────────────────────────────────────────────

_service_instance: Optional[Stage1LoRAService] = None


def get_stage1_service() -> Stage1LoRAService:
    """Return singleton Stage1LoRAService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = Stage1LoRAService()
    return _service_instance
