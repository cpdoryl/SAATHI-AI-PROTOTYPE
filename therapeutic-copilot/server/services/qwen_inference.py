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
        """
        Stream tokens for real-time WebSocket delivery.
        Together AI: uses SSE stream=True on the chat completions endpoint.
        llama.cpp: uses the /completion endpoint with stream=True.
        """
        if self.use_together:
            async for token in self._together_stream(prompt):
                yield token
        else:
            async for token in self._llama_cpp_stream(prompt):
                yield token

    async def _together_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream tokens from Together AI via Server-Sent Events."""
        import httpx
        import json

        headers = {
            "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "https://api.together.xyz/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        token = chunk["choices"][0]["delta"].get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError):
                        continue

    async def _llama_cpp_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream tokens from self-hosted llama.cpp server."""
        import httpx
        import json

        payload = {
            "prompt": prompt,
            "n_predict": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "stop": ["Patient:", "\n\n"],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{settings.LLAMA_CPP_SERVER_URL}/completion",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    try:
                        chunk = json.loads(data_str)
                        token = chunk.get("content", "")
                        if token:
                            yield token
                        if chunk.get("stop"):
                            break
                    except (json.JSONDecodeError, KeyError):
                        continue
