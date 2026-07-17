"""Minimal Gemini REST client for Stage 0 baselines."""

from __future__ import annotations

import json
import os
import time
from urllib import error, request


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


class GeminiClient:
    def __init__(self, api_key: str | None = None, timeout_seconds: int = 30, max_retries: int = 2):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def generate_text(self, system_instruction: str, user_prompt: str) -> str:
        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}],
            },
            "contents": [
                {
                    "parts": [{"text": user_prompt}],
                }
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            GEMINI_API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as response:
                    data = json.loads(response.read().decode("utf-8"))
                break
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"Gemini API HTTP error {exc.code}: {detail}")
            except (error.URLError, TimeoutError) as exc:
                last_error = RuntimeError(f"Gemini API request failed: {exc}")

            if attempt < self.max_retries:
                time.sleep(1.5 * (attempt + 1))
        else:
            raise last_error if last_error else RuntimeError("Gemini API request failed")

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini API returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if "text" in part]
        result = "\n".join(texts).strip()
        if not result:
            raise RuntimeError(f"Gemini API returned no text: {data}")
        return result
