"""Provider implementations. Only 'mock', 'openai' (any OpenAI-compatible endpoint incl. Ollama/vLLM/LM Studio
via AI_BASE_URL) and 'anthropic' exist. Gemini is NOT implemented. Real providers are untested against live APIs
in this repository: see docs/LIMITATIONS.md."""
import time
import httpx
from ..core.config import get_settings
from .base import Provider, ProviderError


class MockProvider(Provider):
    name, model, is_mock = "mock", "deterministic-scaffold", True

    def complete(self, system, user, max_tokens=2000, json_mode=True):
        raise ProviderError("MockProvider does not call an LLM; workflows use deterministic scaffolds")


class _HttpProvider(Provider):
    def __init__(self):
        s = get_settings()
        self.s = s
        self.model = s.ai_model

    def _post(self, url, headers, payload):
        last = None
        for attempt in range(self.s.ai_max_retries + 1):
            try:
                r = httpx.post(url, headers=headers, json=payload, timeout=self.s.ai_timeout)
                if r.status_code in (429, 500, 502, 503, 504) and attempt < self.s.ai_max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                if r.status_code >= 400:
                    raise ProviderError(f"{self.name} returned HTTP {r.status_code}")
                return r.json()
            except httpx.HTTPError as e:
                last = ProviderError(f"{self.name} request failed: {type(e).__name__}")
                if attempt < self.s.ai_max_retries:
                    time.sleep(min(2 ** attempt, 8))
        raise last or ProviderError("provider failure")


class OpenAICompatProvider(_HttpProvider):
    name = "openai"

    def complete(self, system, user, max_tokens=2000, json_mode=True):
        if not self.model:
            raise ProviderError("AI_MODEL is not configured")
        payload = {"model": self.model, "max_tokens": min(max_tokens, self.s.ai_max_output_tokens),
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        h = {"Authorization": f"Bearer {self.s.ai_api_key}"} if self.s.ai_api_key else {}
        d = self._post(self.s.ai_base_url.rstrip("/") + "/chat/completions", h, payload)
        try:
            text = d["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("Unexpected response shape from provider")
        u = d.get("usage") or {}
        return text, {"input_tokens": u.get("prompt_tokens"), "output_tokens": u.get("completion_tokens")}


class AnthropicProvider(_HttpProvider):
    name = "anthropic"

    def complete(self, system, user, max_tokens=2000, json_mode=True):
        if not (self.model and self.s.ai_api_key):
            raise ProviderError("AI_MODEL and AI_API_KEY must be configured")
        payload = {"model": self.model, "max_tokens": min(max_tokens, self.s.ai_max_output_tokens), "system": system,
                   "messages": [{"role": "user", "content": user}]}
        h = {"x-api-key": self.s.ai_api_key, "anthropic-version": "2023-06-01"}
        d = self._post("https://api.anthropic.com/v1/messages", h, payload)
        try:
            text = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
        except (KeyError, TypeError):
            raise ProviderError("Unexpected response shape from provider")
        u = d.get("usage") or {}
        return text, {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens")}


def get_provider() -> Provider:
    name = get_settings().ai_provider.lower()
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAICompatProvider()
    if name == "anthropic":
        return AnthropicProvider()
    raise ProviderError(f"Unsupported AI_PROVIDER '{name}'. Supported: mock, openai, anthropic")
