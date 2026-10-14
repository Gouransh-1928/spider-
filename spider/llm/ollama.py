from typing import Any

import httpx

from spider.core.config import settings


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_host.rstrip("/")
        self.model = settings.ollama_model

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        return str(data.get("response", "")).strip()

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/tags"
                )
                response.raise_for_status()
            return True
        except (httpx.HTTPError, OSError):
            return False


ollama = OllamaClient()