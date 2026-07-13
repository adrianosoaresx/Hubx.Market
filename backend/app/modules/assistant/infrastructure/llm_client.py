from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class LlmResponse:
    available: bool
    text: str = ""
    reason: str = ""


class AssistantLlmClient:
    def complete(self, *, question: str, context: str) -> LlmResponse:
        if not getattr(settings, "ASSISTANT_LLM_ENABLED", False):
            return LlmResponse(available=False, reason="llm-disabled")
        api_key = str(getattr(settings, "ASSISTANT_LLM_API_KEY", "") or "").strip()
        if not api_key:
            return LlmResponse(available=False, reason="llm-api-key-missing")

        provider = str(getattr(settings, "ASSISTANT_LLM_PROVIDER", "openai-compatible") or "").strip().lower()
        if provider not in {"openai", "openai-compatible"}:
            return LlmResponse(available=False, reason="llm-provider-unsupported")

        model = str(getattr(settings, "ASSISTANT_LLM_MODEL", "") or "").strip() or "gpt-4o-mini"
        timeout = float(getattr(settings, "ASSISTANT_LLM_TIMEOUT_SECONDS", 8) or 8)
        base_url = str(getattr(settings, "ASSISTANT_LLM_BASE_URL", "https://api.openai.com/v1") or "").rstrip("/")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Voce e o assistente operacional do Hubx Market para owners/admins. "
                        "Responda em portugues do Brasil, use apenas o contexto fornecido, "
                        "nao invente funcionalidades e diga quando a documentacao nao confirmar algo. "
                        "Nao peça ou exponha segredos, tokens, API keys, dados de pagamento ou PII."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Contexto documentado:\n{context}\n\nPergunta:\n{question}",
                },
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            return LlmResponse(available=False, reason=f"llm-request-failed:{exc.__class__.__name__}")

        try:
            text = str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError):
            return LlmResponse(available=False, reason="llm-response-invalid")
        if not text:
            return LlmResponse(available=False, reason="llm-response-empty")
        return LlmResponse(available=True, text=text)


assistant_llm_client = AssistantLlmClient()

