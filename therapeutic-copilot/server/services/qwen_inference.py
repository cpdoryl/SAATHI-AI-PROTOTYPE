"""
SAATHI AI — Qwen 2.5-7B Inference Service
Dev mode:  Together AI cloud API
Prod mode: llama-cpp-python native bindings (preferred) or llama.cpp HTTP server

Inference routing priority:
  1. LLAMA_CPP_PYTHON_MODEL_PATH set → native llama-cpp-python (fastest, no HTTP overhead)
  2. TOGETHER_API_KEY set            → Together AI cloud API (dev/fallback)
  3. Neither set                     → llama.cpp HTTP server at LLAMA_CPP_SERVER_URL
"""
from config import settings
from loguru import logger
from typing import Optional, AsyncGenerator

# ─── Native llama.cpp model singleton ────────────────────────────────────────
# Loaded once on first use; kept in memory across requests.
_llama_native_model = None


def _get_llama_native_model():
    """Return (or lazily initialise) the llama-cpp-python Llama instance."""
    global _llama_native_model
    if _llama_native_model is None:
        model_path = getattr(settings, "LLAMA_CPP_PYTHON_MODEL_PATH", "")
        if not model_path:
            return None
        try:
            from llama_cpp import Llama
            _llama_native_model = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_gpu_layers=-1,   # offload all layers to GPU if available
                verbose=False,
            )
            logger.info(f"llama-cpp-python model loaded: {model_path}")
        except ImportError:
            logger.warning("llama-cpp-python not installed — falling back to HTTP server")
        except Exception as exc:
            logger.error(f"Failed to load llama-cpp-python model: {exc}")
    return _llama_native_model


class QwenInferenceService:
    """
    Wrapper for Qwen 2.5-7B inference.
    Automatically uses Together AI in dev and llama.cpp in prod.
    """

    def __init__(self):
        self.use_together = bool(settings.TOGETHER_API_KEY)
        self.use_native = bool(getattr(settings, "LLAMA_CPP_PYTHON_MODEL_PATH", ""))
        self.model = settings.TOGETHER_MODEL

    async def generate(self, prompt: str, stage: int = 1, max_tokens: int = 512) -> str:
        """
        Generate a therapeutic response.
        Routes to native llama-cpp-python (prod), Together AI (dev), or llama.cpp HTTP server.
        """
        if self.use_native:
            return self._llama_native_generate(prompt, max_tokens)
        if self.use_together:
            return await self._together_generate(prompt, max_tokens)
        return await self._llama_cpp_generate(prompt, max_tokens)

    def _llama_native_generate(self, prompt: str, max_tokens: int) -> str:
        """
        Run inference directly via llama-cpp-python (synchronous, runs in-process).
        No HTTP round-trip; optimal for single-server production deployment.
        """
        llm = _get_llama_native_model()
        if llm is None:
            raise RuntimeError("llama-cpp-python model not available")
        output = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            stop=["Patient:", "\n\n"],
            echo=False,
        )
        return output["choices"][0]["text"]

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
        Native: llama-cpp-python with stream=True (production, lowest latency).
        Together AI: SSE stream=True on the chat completions endpoint.
        HTTP server: llama.cpp /completion with stream=True.
        """
        if self.use_native:
            async for token in self._llama_native_stream(prompt):
                yield token
        elif self.use_together:
            async for token in self._together_stream(prompt):
                yield token
        else:
            async for token in self._llama_cpp_stream(prompt):
                yield token

    async def _llama_native_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Stream tokens from llama-cpp-python native bindings.
        Uses the llama_cpp.Llama(..., stream=True) generator, bridged to async.
        """
        import asyncio
        llm = _get_llama_native_model()
        if llm is None:
            raise RuntimeError("llama-cpp-python model not available")

        # llama_cpp stream() returns a synchronous generator; run in executor
        # to avoid blocking the event loop.
        loop = asyncio.get_event_loop()

        def _sync_stream():
            return llm(
                prompt,
                max_tokens=512,
                temperature=0.7,
                top_p=0.9,
                stop=["Patient:", "\n\n"],
                echo=False,
                stream=True,
            )

        gen = await loop.run_in_executor(None, _sync_stream)
        for chunk in gen:
            token = chunk["choices"][0].get("text", "")
            if token:
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
        """Stream tokens from self-hosted llama.cpp HTTP server."""
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
