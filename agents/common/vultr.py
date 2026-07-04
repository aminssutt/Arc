"""Single Vultr Serverless Inference client for Arc (issue #24 / AGV.1).

Every specialized agent talks to Vultr's OpenAI-compatible Serverless Inference
endpoint through this one client. It centralises the three things a shared
credit pool needs to survive: a pinned model, a concurrency cap, and
retry/backoff on transient failures.

Design notes
------------
- Model is NEVER hardcoded in a call. `PINNED_MODEL` is read from
  ``contracts/decisions.md`` (single source of truth, marker ``PINNED_MODEL=``)
  and can be overridden with the ``VULTR_MODEL`` env var for tests/benchmarks.
- Concurrency is guarded by a *module-level* ``asyncio.Semaphore`` so every
  client instance in a process shares the same cap (default 2, override with
  ``VULTR_MAX_CONCURRENCY``). This protects the team's shared credit pool.
- ``structured_json`` asks the endpoint for JSON (``response_format``), parses
  it, and re-prompts once if the first reply is not valid JSON.
- Latency is logged per call via the stdlib ``logging`` module (logger name
  ``arc.vultr``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

__all__ = [
    "PINNED_MODEL",
    "DEFAULT_MAX_CONCURRENCY",
    "ChatResult",
    "VultrClient",
    "VultrError",
]

logger = logging.getLogger("arc.vultr")

# --------------------------------------------------------------------------- #
# Static config (endpoint, pinned model, concurrency, retry budget)
# --------------------------------------------------------------------------- #
_DEFAULT_BASE_URL = "https://api.vultrinference.com/v1"

# contracts/decisions.md lives two levels up from this file (agents/common/).
_DECISIONS_PATH = Path(__file__).resolve().parents[2] / "contracts" / "decisions.md"
_PINNED_MODEL_RE = re.compile(r"PINNED_MODEL\s*=\s*(\S+)")


def _read_pinned_model() -> str:
    """Resolve the team-pinned model id.

    Precedence: ``VULTR_MODEL`` env override, then the ``PINNED_MODEL=`` marker
    in ``contracts/decisions.md``. Raising here is intentional: an agent must
    never silently fall back to an unpinned model on a shared credit pool.
    """
    override = os.getenv("VULTR_MODEL")
    if override:
        return override
    try:
        text = _DECISIONS_PATH.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - config error path
        raise VultrError(
            f"Cannot resolve pinned model: {_DECISIONS_PATH} unreadable and "
            "VULTR_MODEL is unset."
        ) from exc
    match = _PINNED_MODEL_RE.search(text)
    if not match:
        raise VultrError(
            f"No 'PINNED_MODEL=' marker found in {_DECISIONS_PATH}; "
            "set VULTR_MODEL or add the marker."
        )
    return match.group(1)


DEFAULT_MAX_CONCURRENCY = 2
_MAX_CONCURRENCY = max(1, int(os.getenv("VULTR_MAX_CONCURRENCY", str(DEFAULT_MAX_CONCURRENCY))))

# Module-level: shared by every VultrClient in the process to cap the shared pool.
_semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_DEFAULT_TIMEOUT = float(os.getenv("VULTR_TIMEOUT", "60"))
_DEFAULT_MAX_RETRIES = 3
_BACKOFF_BASE = 0.5
_BACKOFF_MAX = 8.0
_BACKOFF_JITTER = 0.4


class VultrError(RuntimeError):
    """Any non-recoverable error from the Vultr inference layer."""


@dataclass(slots=True)
class ChatResult:
    """Outcome of one chat completion call."""

    content: str | None
    model: str
    finish_reason: str | None
    latency_ms: float
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


def _extract_content(data: dict[str, Any]) -> tuple[str | None, str | None]:
    """Pull (content, finish_reason) out of an OpenAI-shaped response.

    Reasoning models can return ``content: null`` (their text lands in a
    separate ``reasoning`` field); callers see ``None`` and treat it as no
    usable output.
    """
    choices = data.get("choices") or []
    if not choices:
        return None, None
    choice = choices[0]
    message = choice.get("message") or {}
    return message.get("content"), choice.get("finish_reason")


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def _parse_json(content: str | None) -> dict[str, Any] | None:
    """Best-effort parse of a JSON object from model output.

    Tolerates a single ```json ... ``` markdown fence. Returns ``None`` when the
    content is missing or not a JSON object.
    """
    if not content:
        return None
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = _FENCE_RE.sub("", stripped).strip()
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


class VultrClient:
    """Async client over Vultr's OpenAI-compatible Serverless Inference API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        key = api_key or os.getenv("VULTR_INFERENCE_API_KEY") or os.getenv("VULTR_API_KEY")
        if not key:
            raise VultrError(
                "No API key: set VULTR_INFERENCE_API_KEY (or VULTR_API_KEY) "
                "or pass api_key=."
            )
        self.model = model or PINNED_MODEL
        self.base_url = (base_url or os.getenv("VULTR_INFERENCE_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )

    async def __aenter__(self) -> "VultrClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ----------------------------------------------------------------- #
    # Core call
    # ----------------------------------------------------------------- #
    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
        response_format: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ChatResult:
        """One chat completion, with retry/backoff and concurrency guard.

        ``extra`` is merged verbatim into the request body (e.g.
        ``{"chat_template_kwargs": {"enable_thinking": False}}`` for reasoning
        models). Latency is logged per call.
        """
        used_model = model or self.model
        payload: dict[str, Any] = {
            "model": used_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if extra:
            payload.update(extra)

        data, latency_ms = await self._post_with_retry(
            "/chat/completions", payload, used_model, timeout
        )
        content, finish_reason = _extract_content(data)
        return ChatResult(
            content=content,
            model=used_model,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            usage=data.get("usage") or {},
            raw=data,
        )

    # ----------------------------------------------------------------- #
    # Structured JSON helper
    # ----------------------------------------------------------------- #
    async def structured_json(
        self,
        prompt: str | list[dict[str, Any]],
        *,
        schema: dict[str, Any] | None = None,
        model: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
        extra: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Return a parsed JSON object from the model.

        ``prompt`` may be a plain string (wrapped as a single user message) or a
        full messages list. A JSON Schema, when given, is enforced via
        ``response_format: json_schema``; otherwise ``json_object`` is used.
        Re-prompts once if the first reply is not valid JSON, then raises.
        """
        messages = (
            [{"role": "user", "content": prompt}] if isinstance(prompt, str) else list(prompt)
        )
        if schema is not None:
            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": schema},
            }
        else:
            response_format = {"type": "json_object"}

        result = await self.chat(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            extra=extra,
            timeout=timeout,
        )
        parsed = _parse_json(result.content)
        if parsed is not None:
            return parsed

        logger.warning(
            "vultr %s: invalid JSON (finish=%s), re-prompting once",
            result.model,
            result.finish_reason,
        )
        repair_messages = messages + [
            {"role": "assistant", "content": result.content or ""},
            {
                "role": "user",
                "content": (
                    "Your previous reply was not a valid JSON object. Reply with "
                    "ONLY one valid JSON object, no prose, no markdown fences."
                ),
            },
        ]
        retry = await self.chat(
            repair_messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            extra=extra,
            timeout=timeout,
        )
        parsed = _parse_json(retry.content)
        if parsed is None:
            raise VultrError(
                f"structured_json failed after re-prompt (model={retry.model}, "
                f"finish={retry.finish_reason}): {retry.content!r}"
            )
        return parsed

    # ----------------------------------------------------------------- #
    # Transport with retry/backoff + concurrency guard
    # ----------------------------------------------------------------- #
    async def _post_with_retry(
        self,
        path: str,
        payload: dict[str, Any],
        model: str,
        timeout: float | None,
    ) -> tuple[dict[str, Any], float]:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            start = time.perf_counter()
            try:
                async with _semaphore:
                    response = await self._client.post(
                        path, json=payload, timeout=timeout or self.timeout
                    )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                last_exc = exc
                logger.warning(
                    "vultr %s attempt %d/%d transport error after %.0fms: %s",
                    model, attempt, self.max_retries, latency_ms, exc,
                )
                if attempt == self.max_retries:
                    break
                await self._backoff(attempt)
                continue

            latency_ms = (time.perf_counter() - start) * 1000

            if response.status_code in _RETRYABLE_STATUS:
                logger.warning(
                    "vultr %s attempt %d/%d HTTP %d after %.0fms",
                    model, attempt, self.max_retries, response.status_code, latency_ms,
                )
                if attempt == self.max_retries:
                    raise VultrError(
                        f"vultr HTTP {response.status_code} after {self.max_retries} "
                        f"attempts: {response.text[:300]}"
                    )
                await self._backoff(attempt, response.headers.get("retry-after"))
                continue

            if response.status_code >= 400:
                raise VultrError(
                    f"vultr HTTP {response.status_code}: {response.text[:300]}"
                )

            logger.info(
                "vultr %s HTTP %d in %.0fms (attempt %d)",
                model, response.status_code, latency_ms, attempt,
            )
            return response.json(), latency_ms

        raise VultrError(
            f"vultr request failed after {self.max_retries} attempts"
        ) from last_exc

    async def _backoff(self, attempt: int, retry_after: str | None = None) -> None:
        """Sleep before the next attempt: honour Retry-After, else exp backoff + jitter."""
        delay: float | None = None
        if retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = None
        if delay is None:
            delay = min(_BACKOFF_BASE * (2 ** (attempt - 1)), _BACKOFF_MAX)
        delay += random.uniform(0, _BACKOFF_JITTER)
        await asyncio.sleep(delay)


# Resolved at import so a missing pin fails fast and loudly.
PINNED_MODEL = _read_pinned_model()
