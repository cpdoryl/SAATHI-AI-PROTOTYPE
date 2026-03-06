"""
SAATHI AI — Qwen 2.5-7B Inference Service
Dev mode: Together AI cloud API
Prod mode: Self-hosted llama.cpp on E2E Networks Mumbai
"""
from config import settings
from loguru import logger
from typing import Optional, AsyncGenerator


class QwenInferenceService:
    """
    Wrapper for Qwen 2.5-7B inference.
    Automatically uses Together AI in dev and llama.cpp in prod.
    """

    def __init__(self):
        self.use_together = bool(settings.TOGETHER_API_KEY)
        self.model = settings.TOGETHER_MODEL

    async def generate(self, prompt: str, stage: int = 1, max_tokens: int = 512) -> str:
        """
        Generate a therapeutic response.
        Routes to Together AI (dev) or llama.cpp (prod).
        """
        if self.use_together:
            return await self._together_generate(prompt, max_tokens)
        else:
            return await self._llama_cpp_generate(prompt, max_tokens)

    async def _together_generate(self, prompt: str, max_tokens: int) -> str:
        """Call Together AI API for Qwen 2.5-7B inference."""
        import httpx
        headers = {
            "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _llama_cpp_generate(self, prompt: str, max_tokens: int) -> str:
        """Call self-hosted llama.cpp server for inference."""
        import httpx
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stop": ["Patient:", "\n\n"],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.LLAMA_CPP_SERVER_URL}/completion",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json().get("content", "")

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream tokens for real-time WebSocket delivery."""
        # TODO: Implement token streaming from Together AI / llama.cpp
        response = await self.generate(prompt)
        for word in response.split():
            yield word + " "
