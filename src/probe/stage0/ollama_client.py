"""Minimal Ollama REST client for local Stage 0 baselines."""

from __future__ import annotations

import json
import os
from urllib import error, request


OLLAMA_API_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434") + "/api/generate"


class OllamaClient:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

    def generate_text(self, system_instruction: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "system": system_instruction,
            "prompt": user_prompt,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            OLLAMA_API_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        text = data.get("response", "").strip()
        if not text:
            raise RuntimeError(f"Ollama returned no text: {data}")
        return text
