# Team decisions

Living record of cross-team technical decisions for Arc. Each entry is dated and
notes its approval status. The agentic lane reads the inference pin from here.

<!--
  MACHINE-READABLE PIN (do not remove): agents/common/vultr.py parses the line
  below to resolve the model. Override at runtime with the VULTR_MODEL env var.
-->
<!-- PINNED_MODEL=deepseek-ai/DeepSeek-V4-Flash -->

---

## Pinned inference model  [PROPOSED — approval @aminssutt via PR]

**Pinned model:** `deepseek-ai/DeepSeek-V4-Flash`
**Endpoint:** `https://api.vultrinference.com/v1` (Vultr Serverless Inference, OpenAI-compatible)
**Date:** 2026-07-04 · **Author:** @vgtray (dev-backend)

Every agent uses this one model through `agents/common/vultr.py`. No agent hardcodes
a model id; the client reads the `PINNED_MODEL=` marker above (env `VULTR_MODEL`
overrides for tests/benchmarks).

### Models available on the shared account (2026-07-04)

`MiniMaxAI/MiniMax-M2.7`, `Qwen/Qwen3.5-397B-A17B`, `Qwen/Qwen3.6-27B`,
`XiaomiMiMo/MiMo-V2.5-Pro`, `deepseek-ai/DeepSeek-V4-Flash`, `moonshotai/Kimi-K2.6`,
`nvidia/DeepSeek-V3.2-NVFP4`, `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16`,
`nvidia/Nemotron-Cascade-2-30B-A3B`, `zai-org/GLM-5.2-FP8`, plus the
`vultr/VultronRetriever*` retrieval models.

---

## Concurrency budget

- **Module-level `asyncio.Semaphore`, default 2**, shared by every `VultrClient`
  in a process. Override with `VULTR_MAX_CONCURRENCY`.
- Rationale: one shared credit pool ($200 team budget) + a small candidate pool.
  Two concurrent requests keep the orchestrator's fan-out responsive without
  risking 429s or draining credits under load. Raise deliberately, not by default.
- Per-call defaults: `timeout=60s` (env `VULTR_TIMEOUT`), retry **3×** on
  `429/5xx/timeout` with exponential backoff + jitter (honours `Retry-After`).

---

## Rationale — model bench (real calls, 2026-07-04)

Benched the three shortlisted candidates through the actual client:
`response_format=json_object`, `max_tokens=100` (the system's structured-output
budget), `temperature=0`, 5 sequential calls each, JSON parsed from `content`.

| Model | JSON ok / 5 | Median latency | Range | Notes |
|-------|-------------|----------------|-------|-------|
| **deepseek-ai/DeepSeek-V4-Flash** | **5/5** | **1481 ms** | 1336–2211 ms | Non-reasoning, clean JSON, no special params, no stalls |
| zai-org/GLM-5.2-FP8 | 5/5 | 1370 ms* | 1217–1489 ms* | Reasoning model: needs `chat_template_kwargs.enable_thinking=false`; **4 endpoint stalls >60 s / 5 calls** (recovered on retry) — tail latency unacceptable |
| moonshotai/Kimi-K2.6 | 0/5 | — | — | Reasoning-only: `content` stays `null` under budget. Even at `max_tokens=500` it burned 250 reasoning tokens and still emitted no JSON (`finish=length`). `enable_thinking=false`/`reasoning_effort=none` do not disable it. |

\* GLM's median counts the successful attempt only; real wall-clock included
repeated 60 s timeouts, so effective p90+ is >60 s.

**Decision:** `DeepSeek-V4-Flash` wins on the three axes that matter for a
multi-agent pipeline on a shared pool: (1) reliability — 5/5 valid JSON with no
timeouts; (2) tail latency — tight 1.3–2.2 s band vs GLM's 60 s+ stalls; (3)
simplicity/cost — non-reasoning, so no per-call `enable_thinking` workaround, ~27
completion tokens vs 50+ burned on reasoning. Kimi-K2.6 is unusable for structured
extraction under any reasonable token budget.

**Live smoke (AC #24):** 5 consecutive `structured_json()` calls on the pinned
model parsed 5/5 (3.0–5.4 s each). One call's first attempt truncated at the
100-token cap (`finish=length` → invalid JSON) and the client's automatic
single re-prompt recovered it — the JSON safety net is proven in production.

> Agents producing larger payloads should raise `max_tokens` past 100 to avoid
> truncation; the re-prompt is a safety net, not a substitute for enough tokens.
