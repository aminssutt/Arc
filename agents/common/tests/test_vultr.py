"""Unit tests for VultrClient (issue #24) -- fully network-mocked.

Vultr's OpenAI-compatible Serverless Inference endpoint is faked with
``httpx.MockTransport``. VultrClient has no client-injection hook, so each test
builds a client, discards the real ``httpx.AsyncClient`` it created, and swaps in
a MockTransport-backed one -- no real socket is ever opened and no real API key
is read (``api_key="test-key"`` is always passed explicitly; ``.env`` is never
loaded by the module).

Coverage map (issue #24 acceptance criteria):
1. ``chat`` happy path -> populated ChatResult.
2. ``structured_json`` parses valid JSON; on an invalid reply it re-prompts
   EXACTLY once, then raises cleanly if still invalid.
3. Retry/backoff: 429 honours ``Retry-After``; 5xx retried up to 3x then clean
   error; timeout retried.
4. Semaphore: the module concurrency cap bounds simultaneous in-flight requests.
5. Model resolution: ``PINNED_MODEL=`` marker parsed from decisions.md, with the
   ``VULTR_MODEL`` env override taking precedence.
6. Truncation (``finish_reason=length``) that yields invalid JSON triggers the
   single-re-prompt safety net.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

import httpx
import pytest

import agents.common.vultr as vultr
from agents.common.vultr import ChatResult, VultrClient, VultrError


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _chat_response(
    content: str | None,
    *,
    finish_reason: str = "stop",
    status: int = 200,
    usage: dict | None = None,
    model: str = "pinned-x",
    headers: dict | None = None,
) -> httpx.Response:
    """Build an OpenAI-shaped chat completion response."""
    return httpx.Response(
        status,
        headers=headers or {},
        json={
            "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
            "usage": usage or {"total_tokens": 1},
            "model": model,
        },
    )


@contextlib.asynccontextmanager
async def vultr_client(handler, *, model: str = "pinned-x", max_retries: int = 3):
    """A VultrClient whose transport is a MockTransport (no real network).

    The real AsyncClient built in ``__init__`` is closed and replaced; api_key is
    a dummy so the constructor's key guard passes without touching any env/.env.
    """
    vc = VultrClient(api_key="test-key", model=model, max_retries=max_retries)
    await vc._client.aclose()  # discard the real client we won't use
    vc._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=vc.base_url
    )
    try:
        yield vc
    finally:
        await vc._client.aclose()


@pytest.fixture
def no_sleep(monkeypatch):
    """Neutralise backoff sleeps and record the delays that were requested."""
    recorded: list[float] = []

    async def fake_sleep(delay, *args, **kwargs):
        recorded.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded


# --------------------------------------------------------------------------- #
# 1. chat happy path
# --------------------------------------------------------------------------- #
class TestChat:
    @pytest.mark.asyncio
    async def test_chat_nominal_populates_result(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return _chat_response("pong", usage={"total_tokens": 5}, model="pinned-x")

        async with vultr_client(handler, model="pinned-x") as vc:
            res = await vc.chat([{"role": "user", "content": "ping"}], max_tokens=32)

        # Result is fully populated from the response.
        assert isinstance(res, ChatResult)
        assert res.content == "pong"
        assert res.finish_reason == "stop"
        assert res.model == "pinned-x"
        assert res.usage == {"total_tokens": 5}
        assert res.latency_ms >= 0.0
        assert res.raw["choices"][0]["message"]["content"] == "pong"
        # The request carried the pinned model + our message + params.
        body = json.loads(seen[0].content)
        assert body["model"] == "pinned-x"
        assert body["messages"] == [{"role": "user", "content": "ping"}]
        assert body["max_tokens"] == 32
        assert len(seen) == 1


# --------------------------------------------------------------------------- #
# 2. structured_json: parse, single re-prompt, clean failure
# --------------------------------------------------------------------------- #
class TestStructuredJson:
    @pytest.mark.asyncio
    async def test_valid_json_first_try_no_reprompt(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request):
            seen.append(request)
            return _chat_response('{"answer": 42}')

        async with vultr_client(handler) as vc:
            out = await vc.structured_json("give me json")

        assert out == {"answer": 42}
        assert len(seen) == 1  # no re-prompt

    @pytest.mark.asyncio
    async def test_invalid_then_valid_triggers_exactly_one_reprompt(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request):
            seen.append(request)
            if len(seen) == 1:
                return _chat_response("sorry, here is your data: not json at all")
            return _chat_response('{"ok": true}')

        async with vultr_client(handler) as vc:
            out = await vc.structured_json("give me json")

        assert out == {"ok": True}
        assert len(seen) == 2  # exactly one re-prompt
        # The re-prompt appended the repair instruction as a new user turn.
        repair_body = json.loads(seen[1].content)
        assert repair_body["messages"][-1]["role"] == "user"
        assert "valid JSON object" in repair_body["messages"][-1]["content"]

    @pytest.mark.asyncio
    async def test_still_invalid_after_reprompt_raises_cleanly(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request):
            seen.append(request)
            return _chat_response("still not json")

        async with vultr_client(handler) as vc:
            with pytest.raises(VultrError, match="structured_json failed after re-prompt"):
                await vc.structured_json("give me json")

        assert len(seen) == 2  # original + exactly one re-prompt, then give up

    @pytest.mark.asyncio
    async def test_schema_sets_json_schema_response_format(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request):
            seen.append(request)
            return _chat_response('{"x": 1}')

        schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        async with vultr_client(handler) as vc:
            await vc.structured_json("go", schema=schema)

        rf = json.loads(seen[0].content)["response_format"]
        assert rf["type"] == "json_schema"
        assert rf["json_schema"]["schema"] == schema

    @pytest.mark.asyncio
    async def test_markdown_fenced_json_is_parsed(self) -> None:
        def handler(request):
            return _chat_response('```json\n{"fenced": true}\n```')

        async with vultr_client(handler) as vc:
            out = await vc.structured_json("go")
        assert out == {"fenced": True}


# --------------------------------------------------------------------------- #
# 6. Truncation (finish_reason=length) -> single re-prompt safety net
# --------------------------------------------------------------------------- #
class TestTruncationReprompt:
    @pytest.mark.asyncio
    async def test_length_truncation_invalid_json_triggers_single_reprompt(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request):
            seen.append(request)
            if len(seen) == 1:
                # Truncated mid-object: invalid JSON, finish_reason == "length".
                return _chat_response('{"partial": "va', finish_reason="length")
            return _chat_response('{"complete": true}')

        async with vultr_client(handler) as vc:
            out = await vc.structured_json("give me json")

        assert out == {"complete": True}
        assert len(seen) == 2  # the truncated reply set off exactly one re-prompt


# --------------------------------------------------------------------------- #
# 3. Retry / backoff
# --------------------------------------------------------------------------- #
class TestRetryBackoff:
    @pytest.mark.asyncio
    async def test_429_honours_retry_after(self, no_sleep) -> None:
        seen: list[httpx.Request] = []

        def handler(request):
            seen.append(request)
            if len(seen) == 1:
                return _chat_response(None, status=429, headers={"Retry-After": "2.5"})
            return _chat_response("ok")

        async with vultr_client(handler) as vc:
            res = await vc.chat([{"role": "user", "content": "hi"}])

        assert res.content == "ok"
        assert len(seen) == 2
        # One backoff, and it honoured Retry-After (2.5s) plus bounded jitter.
        assert len(no_sleep) == 1
        assert 2.5 <= no_sleep[0] <= 2.5 + vultr._BACKOFF_JITTER

    @pytest.mark.asyncio
    async def test_5xx_retried_max_then_clean_error(self, no_sleep) -> None:
        seen: list[httpx.Request] = []

        def handler(request):
            seen.append(request)
            return _chat_response(None, status=503)

        async with vultr_client(handler, max_retries=3) as vc:
            with pytest.raises(VultrError, match="HTTP 503 after 3 attempts"):
                await vc.chat([{"role": "user", "content": "hi"}])

        assert len(seen) == 3            # exactly max_retries attempts
        assert len(no_sleep) == 2        # backoff between attempts, not after the last

    @pytest.mark.asyncio
    async def test_timeout_retried_then_success(self, no_sleep) -> None:
        seen: list[httpx.Request] = []

        async def handler(request):
            seen.append(request)
            if len(seen) == 1:
                raise httpx.ReadTimeout("simulated timeout", request=request)
            return _chat_response("recovered")

        async with vultr_client(handler) as vc:
            res = await vc.chat([{"role": "user", "content": "hi"}])

        assert res.content == "recovered"
        assert len(seen) == 2
        assert len(no_sleep) == 1

    @pytest.mark.asyncio
    async def test_persistent_timeout_raises_after_max_retries(self, no_sleep) -> None:
        seen: list[httpx.Request] = []

        async def handler(request):
            seen.append(request)
            raise httpx.ConnectTimeout("always times out", request=request)

        async with vultr_client(handler, max_retries=3) as vc:
            with pytest.raises(VultrError, match="failed after 3 attempts") as exc_info:
                await vc.chat([{"role": "user", "content": "hi"}])

        assert len(seen) == 3
        assert len(no_sleep) == 2
        assert isinstance(exc_info.value.__cause__, httpx.TimeoutException)

    @pytest.mark.asyncio
    async def test_non_retryable_4xx_raises_immediately(self, no_sleep) -> None:
        seen: list[httpx.Request] = []

        def handler(request):
            seen.append(request)
            return _chat_response(None, status=400)

        async with vultr_client(handler, max_retries=3) as vc:
            with pytest.raises(VultrError, match="HTTP 400"):
                await vc.chat([{"role": "user", "content": "hi"}])

        assert len(seen) == 1      # 400 is not retried
        assert no_sleep == []      # no backoff


# --------------------------------------------------------------------------- #
# 4. Semaphore concurrency cap
# --------------------------------------------------------------------------- #
class TestConcurrency:
    @pytest.mark.asyncio
    async def test_semaphore_bounds_simultaneous_requests(self, monkeypatch) -> None:
        state = {"current": 0, "max": 0}

        async def handler(request):
            state["current"] += 1
            state["max"] = max(state["max"], state["current"])
            await asyncio.sleep(0.02)  # hold the slot so tasks overlap
            state["current"] -= 1
            return _chat_response("ok")

        # Force the shared cap to 2 for this test (the code reads the module global
        # `_semaphore` at call time, so patching it here is honoured).
        monkeypatch.setattr(vultr, "_semaphore", asyncio.Semaphore(2))

        async with vultr_client(handler) as vc:
            await asyncio.gather(
                *(vc.chat([{"role": "user", "content": "hi"}]) for _ in range(6))
            )

        # Six tasks, cap of two: concurrency reached the cap but never exceeded it.
        assert state["max"] == 2


# --------------------------------------------------------------------------- #
# 5. Model resolution (marker + env override)
# --------------------------------------------------------------------------- #
class TestModelResolution:
    def test_env_override_takes_precedence(self, monkeypatch, tmp_path) -> None:
        # Even with a different marker on disk, VULTR_MODEL wins.
        decisions = tmp_path / "decisions.md"
        decisions.write_text("PINNED_MODEL=file/model-on-disk\n", encoding="utf-8")
        monkeypatch.setattr(vultr, "_DECISIONS_PATH", decisions)
        monkeypatch.setenv("VULTR_MODEL", "env/override-model")

        assert vultr._read_pinned_model() == "env/override-model"

    def test_reads_marker_from_decisions_file(self, monkeypatch, tmp_path) -> None:
        decisions = tmp_path / "decisions.md"
        decisions.write_text("intro\n<!-- PINNED_MODEL=org/pinned-8b -->\nmore\n", encoding="utf-8")
        monkeypatch.setattr(vultr, "_DECISIONS_PATH", decisions)
        monkeypatch.delenv("VULTR_MODEL", raising=False)

        assert vultr._read_pinned_model() == "org/pinned-8b"

    def test_marker_regex_tolerates_spaces(self, monkeypatch, tmp_path) -> None:
        decisions = tmp_path / "decisions.md"
        decisions.write_text("PINNED_MODEL   =    spaced/model-4b\n", encoding="utf-8")
        monkeypatch.setattr(vultr, "_DECISIONS_PATH", decisions)
        monkeypatch.delenv("VULTR_MODEL", raising=False)

        assert vultr._read_pinned_model() == "spaced/model-4b"

    def test_missing_marker_raises(self, monkeypatch, tmp_path) -> None:
        decisions = tmp_path / "decisions.md"
        decisions.write_text("no marker here at all\n", encoding="utf-8")
        monkeypatch.setattr(vultr, "_DECISIONS_PATH", decisions)
        monkeypatch.delenv("VULTR_MODEL", raising=False)

        with pytest.raises(VultrError, match="No 'PINNED_MODEL='"):
            vultr._read_pinned_model()


# --------------------------------------------------------------------------- #
# API key guard (no real key / no .env auto-load)
# --------------------------------------------------------------------------- #
class TestApiKeyGuard:
    def test_missing_key_raises_without_reading_env_file(self, monkeypatch) -> None:
        monkeypatch.delenv("VULTR_INFERENCE_API_KEY", raising=False)
        monkeypatch.delenv("VULTR_API_KEY", raising=False)
        with pytest.raises(VultrError, match="No API key"):
            VultrClient()
