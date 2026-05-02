import asyncio
from typing import Dict, List

import httpx


class AIServiceError(Exception):
    """Raised when AI service fails after retries."""
    pass


class AIService:
    """LLM API client (OpenAI-compatible) with retry logic."""

    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: float = 0.7, max_tokens: int = 1024):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = httpx.AsyncClient(timeout=30)
        self._max_retries = 2

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send chat completion request with retry and return assistant's reply."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.HTTPStatusError, httpx.TimeoutException,
                    httpx.RequestError, KeyError) as e:
                last_error = e
                if attempt < self._max_retries:
                    await asyncio.sleep(1.5 ** attempt)
                continue

        raise AIServiceError(f"AI service failed after {self._max_retries + 1} attempts"
                             f" [{type(last_error).__name__}: {last_error}]"
                             ) from last_error

    async def close(self):
        await self._client.aclose()
