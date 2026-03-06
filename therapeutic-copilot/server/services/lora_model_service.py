"""
SAATHI AI — LoRA Model Service
Manages switching between Stage 1 (r=8) and Stage 2 (r=16) LoRA adapters.
Only active when using self-hosted llama.cpp in production.
"""
from loguru import logger


LORA_ADAPTERS = {
    1: {
        "name": "stage1-lead-generation",
        "rank": 8,
        "training_examples": 634,
        "path": "/models/lora-adapters/stage1-r8.gguf",
        "description": "Fine-tuned for lead generation, booking conversion, FAQ handling",
    },
    2: {
        "name": "stage2-therapeutic-copilot",
        "rank": 16,
        "training_examples": 3017,
        "path": "/models/lora-adapters/stage2-r16.gguf",
        "description": "Fine-tuned for 11-step therapeutic conversations, CBT/DBT techniques",
    },
}


class LoRAModelService:
    """Manages LoRA adapter selection based on patient stage."""

    def __init__(self):
        self._current_stage = None

    def get_adapter_config(self, stage: int) -> dict:
        """Return LoRA adapter config for the given stage."""
        return LORA_ADAPTERS.get(stage, LORA_ADAPTERS[1])

    async def switch_adapter(self, stage: int) -> bool:
        """
        Switch the active LoRA adapter on the llama.cpp server.
        Only called in production (self-hosted) mode.
        """
        if self._current_stage == stage:
            return True  # Already loaded

        config = self.get_adapter_config(stage)
        logger.info(f"Switching to LoRA adapter: {config['name']} (rank={config['rank']})")

        # TODO: Call llama.cpp API to hot-swap LoRA adapter
        self._current_stage = stage
        return True

    def get_system_prompt_modifier(self, stage: int) -> str:
        """Return stage-specific prompt modifier for the LoRA adapter."""
        if stage == 1:
            return (
                "You are operating in Lead Generation mode. "
                "Your priority is empathetic discovery and booking conversion."
            )
        return (
            "You are operating in Therapeutic Co-Pilot mode. "
            "Apply evidence-based techniques: CBT, DBT, ACT, Psychodynamic approaches."
        )
