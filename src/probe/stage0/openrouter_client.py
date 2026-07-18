from __future__ import annotations

import json
import os
import time
from urllib import error, request


OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_URL = OPENROUTER_BASE_URL + "/chat/completions"

DEFAULT_MODELS = [
    "meta-llama/llama-3.3-70b-instruct",
]


class OpenRouterClient:
    def __init__(
        self,
        api_key: str | None = None,
        models: list[str] | None = None,
        temperature: float = 0.2,
        timeout_seconds: int = 60,
        max_retries_per_model: int = 1,
        max_tokens: int | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured")
        env_models = os.getenv("OPENROUTER_MODELS")
        self.models = models or (
            [m.strip() for m in env_models.split(",") if m.strip()] if env_models else DEFAULT_MODELS
        )
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_retries_per_model = max_retries_per_model
        env_max_tokens = os.getenv("OPENROUTER_MAX_TOKENS")
        self.max_tokens = max_tokens if max_tokens is not None else (int(env_max_tokens) if env_max_tokens else None)
        self.last_model_used: str | None = None

    def _call_one(self, model: str, system_instruction: str, user_prompt: str) -> str:
        payload = {
            "model": model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            OPENROUTER_API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://local/probe"),
                "X-Title": os.getenv("OPENROUTER_TITLE", "PROBE Stage 0"),
            },
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"OpenRouter returned no choices: {data}")
        text = choices[0].get("message", {}).get("content", "").strip()
        if not text:
            raise RuntimeError(f"OpenRouter returned no text: {data}")
        return text

    def generate_text(self, system_instruction: str, user_prompt: str) -> str:
        last_error: Exception | None = None
        for model in self.models:
            for attempt in range(self.max_retries_per_model + 1):
                try:
                    text = self._call_one(model, system_instruction, user_prompt)
                    self.last_model_used = model
                    return text
                except error.HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")
                    last_error = RuntimeError(f"OpenRouter HTTP {exc.code} on {model}: {detail}")
                    if exc.code in (429, 402):
                        time.sleep(1.0 * (attempt + 1))
                        break
                    if 500 <= exc.code < 600:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    break
                except (error.URLError, TimeoutError) as exc:
                    last_error = RuntimeError(f"OpenRouter request failed on {model}: {exc}")
                    time.sleep(1.0 * (attempt + 1))
                    continue
        raise last_error if last_error else RuntimeError("OpenRouter: all models failed")
