"""Minimal Groq-compatible chat client for Stage 0 baselines."""

from __future__ import annotations

import json
import os
from urllib import error, request


GROQ_API_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1") + "/chat/completions"


class GroqClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    def generate_text(self, system_instruction: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            GROQ_API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Groq HTTP error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Groq request failed: {exc}") from exc

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"Groq returned no choices: {data}")
        text = choices[0].get("message", {}).get("content", "").strip()
        if not text:
            raise RuntimeError(f"Groq returned no text: {data}")
        return text
