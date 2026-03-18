#!/usr/bin/env python3
"""
Meta-Model Pattern Detector Service - Production Integration

Singleton service for detecting linguistic meta-model patterns in therapeutic utterances.
Uses Flan-T5 (fine-tuned with LoRA) + AllenNLP SRL for pattern detection.

Integration point:
  therapeutic_ai_service.py → meta_model_detector_service.detect(utterance)
    │
    ├─ SRL: Extract semantic structure
    ├─ Flan-T5: Classify patterns
    └─ Return: [{"pattern_subtype": "...", "recovery_questions": [...]}]
"""

import torch
import time
import json
from typing import Optional, Dict, List
from pathlib import Path

try:
    from transformers import AutoTokenizer, T5ForConditionalGeneration
    from peft import PeftModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("[MetaModelDetectorService] Warning: transformers not installed. Service will degrade gracefully.")

try:
    from allennlp.predictors.predictor import Predictor
    ALLENNLP_AVAILABLE = True
except ImportError:
    ALLENNLP_AVAILABLE = False
    print("[MetaModelDetectorService] Warning: allennlp not installed. SRL features disabled.")


class MetaModelDetectorService:
    """
    Production service for meta-model pattern detection.
    Uses singleton pattern (one instance per server).
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path: str = "./ml_models/meta_model_detector"):
        """
        Initialize service.

        Args:
            model_path: Path to fine-tuned Flan-T5 model directory
        """
        if self._initialized:
            return

        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.srl_predictor = None
        self.recovery_questions = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Pattern taxonomy
        self.pattern_taxonomy = {
            "unspecified_referential_index": "deletion",
            "unspecified_verb": "deletion",
            "comparative_deletion": "deletion",
            "universal_quantifiers": "generalization",
            "modal_operators_necessity": "generalization",
            "modal_operators_possibility": "generalization",
            "nominalization": "distortion",
            "mind_reading": "distortion",
            "cause_and_effect": "distortion",
            "complex_equivalence": "distortion",
            "presupposition": "distortion",
        }

        # Try to load model and SRL
        self._load_models()
        self._load_recovery_questions()

        self.is_ready = self.model is not None
        self._initialized = True

        if self.is_ready:
            print("[MetaModelDetectorService] Model loaded successfully.")
        else:
            print("[MetaModelDetectorService] Model not available; service degraded.")

    def _load_models(self):
        """Load Flan-T5 and AllenNLP SRL models."""
        if not TRANSFORMERS_AVAILABLE:
            return

        try:
            model_dir = Path(self.model_path)
            if model_dir.exists():
                self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
                if (model_dir / "adapter_config.json").exists():
                    # LoRA adapter — load base model then merge adapters
                    base = T5ForConditionalGeneration.from_pretrained(
                        "google/flan-t5-large"
                    )
                    peft_model = PeftModel.from_pretrained(base, str(model_dir))
                    self.model = peft_model.merge_and_unload()
                else:
                    # Fully merged model
                    self.model = T5ForConditionalGeneration.from_pretrained(
                        str(model_dir)
                    )
                self.model.eval()
                self.model.to(self.device)
        except Exception as e:
            print(f"[MetaModelDetectorService] Failed to load Flan-T5: {e}")

        # Load SRL (optional but recommended)
        if ALLENNLP_AVAILABLE:
            try:
                self.srl_predictor = Predictor.from_path(
                    "https://storage.googleapis.com/allennlp-public-models/"
                    "structured-prediction-srl-bert.2020.12.15.tar.gz"
                )
            except Exception as e:
                print(f"[MetaModelDetectorService] Failed to load SRL: {e}")

    def _load_recovery_questions(self):
        """Load recovery question templates."""
        try:
            recovery_path = Path(self.model_path) / "recovery_questions.json"
            if recovery_path.exists():
                with open(recovery_path) as f:
                    self.recovery_questions = json.load(f)
        except Exception as e:
            print(f"[MetaModelDetectorService] Failed to load recovery questions: {e}")

    def detect(self, utterance: str) -> Optional[Dict]:
        """
        Detect meta-model patterns in utterance.

        Args:
            utterance: User message text

        Returns:
            Dict with:
            - patterns_detected: List of detected patterns
            - pattern_count: Number of patterns detected
            - srl_output: Semantic role labeling output (if available)
            - processing_time_ms: Inference latency
            or None if model not ready
        """
        if not self.is_ready or self.model is None:
            return None

        start_time = time.time()

        try:
            # Step 1: Get SRL output if available
            srl_text = ""
            if self.srl_predictor:
                try:
                    srl_result = self.srl_predictor.predict(sentence=utterance)
                    srl_text = self._format_srl_output(srl_result)
                except Exception as e:
                    print(f"[MetaModelDetectorService] SRL error: {e}")

            # Step 2: Build Flan-T5 input
            input_text = self._build_prompt(utterance, srl_text)

            # Step 3: Generate pattern predictions
            inputs = self.tokenizer(
                input_text,
                return_tensors='pt',
                max_length=256,
                truncation=True,
                padding='max_length'
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    inputs['input_ids'],
                    attention_mask=inputs['attention_mask'],
                    max_length=128,
                    num_beams=4,
                    early_stopping=True,
                    do_sample=False
                )

            output_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Step 4: Parse patterns
            patterns = self._parse_pattern_output(output_text, utterance)

            return {
                "patterns_detected": patterns,
                "pattern_count": len(patterns),
                "srl_output": srl_text,
                "processing_time_ms": round((time.time() - start_time) * 1000, 1),
            }

        except Exception as e:
            print(f"[MetaModelDetectorService] Inference error: {e}")
            return None

    def _build_prompt(self, utterance: str, srl_text: str) -> str:
        """Build Flan-T5 input prompt."""
        prompt = """Identify all linguistic meta-model patterns in the utterance.
Output format: CATEGORY|SUBTYPE|MATCHED_TEXT (one pattern per line)

Categories: deletion, generalization, distortion

Subtypes:
  deletion: unspecified_referential_index, unspecified_verb, comparative_deletion
  generalization: universal_quantifiers, modal_operators_necessity, modal_operators_possibility
  distortion: nominalization, mind_reading, cause_and_effect, complex_equivalence, presupposition
"""
        if srl_text:
            prompt += f"\nSRL Analysis: {srl_text}\n"

        prompt += f"\nUtterance: {utterance}\n\nPatterns:"
        return prompt

    def _format_srl_output(self, srl_result: Dict) -> str:
        """Format AllenNLP SRL output."""
        srl_parts = []
        for verb_info in srl_result.get('verbs', []):
            desc = verb_info.get('description', '')
            srl_parts.append(f"{verb_info['verb']}: {desc}")
        return " | ".join(srl_parts)

    def _parse_pattern_output(self, output_text: str, utterance: str) -> List[Dict]:
        """Parse Flan-T5 output: CATEGORY|SUBTYPE|MATCHED_TEXT format."""
        patterns = []

        for line in output_text.strip().split('\n'):
            line = line.strip()
            if not line or '|' not in line:
                continue

            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 2:
                continue

            category = parts[0].lower()
            subtype = parts[1]
            matched_text = parts[2] if len(parts) > 2 else utterance

            # Validate pattern subtype
            if subtype not in self.pattern_taxonomy:
                continue

            # Get recovery questions
            recovery_qs = self.recovery_questions.get(subtype, [])
            if isinstance(recovery_qs, list):
                recovery_qs = recovery_qs[:2]  # Take first 2
            else:
                recovery_qs = []

            patterns.append({
                "pattern_category": category,
                "pattern_subtype": subtype,
                "matched_text": matched_text,
                "confidence": 0.85,  # Could be enhanced with beam confidence scores
                "recovery_questions": recovery_qs,
                "severity": self._assess_severity(subtype, matched_text),
            })

        return patterns

    def _assess_severity(self, subtype: str, matched_text: str) -> str:
        """Assess pattern severity (low/moderate/high) for clinical guidance."""
        high_severity = {'mind_reading', 'cause_and_effect', 'complex_equivalence', 'presupposition'}
        if subtype in high_severity:
            return "high"
        elif subtype in {'nominalization', 'modal_operators_possibility'}:
            return "moderate"
        return "low"

    def build_prompt_context(self, meta_result: Optional[Dict]) -> str:
        """
        Build LLM system prompt context from pattern detection.

        Args:
            meta_result: Output from detect()

        Returns:
            String block to inject into LLM system prompt
        """
        if not meta_result or not meta_result.get('patterns_detected'):
            return ""

        patterns = meta_result['patterns_detected']
        block = "## Meta-Model Patterns Detected (NLP Linguistic Analysis)\n\n"

        for i, pattern in enumerate(patterns[:3]):  # Max 3 patterns
            block += f"""### Pattern {i + 1}: {pattern['pattern_subtype'].replace('_', ' ').title()}
- **Category**: {pattern['pattern_category'].title()}
- **Matched Text**: "{pattern['matched_text']}"
- **Severity**: {pattern.get('severity', 'moderate').title()}
- **Recovery Questions** (choose ONE to ask naturally):
"""
            for rq in pattern.get('recovery_questions', [])[:2]:
                block += f"  - {rq}\n"

        block += """
**Instructions for this turn**:
- Choose ONE recovery question if it feels natural (not all at once)
- Frame gently: "I'm curious..." / "I wonder..." / "I notice..."
- Only use when user seems ready to explore deeper
- For high-severity patterns (mind-reading, cause-effect), address the underlying belief with compassion
- Do NOT use recovery questions as interrogation — keep conversational flow
"""
        return block


def get_meta_model_detector_service() -> MetaModelDetectorService:
    """Get singleton instance of MetaModelDetectorService."""
    return MetaModelDetectorService()
