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

---

## Canonical Citation + agent→event transform  [PROPOSED — approval @aminssutt (adapters) + @simerugby (events)]

**Date:** 2026-07-04 · **Author:** @vgtray (dev-backend) · **Source:** audit stage-A P0-1 (#76), re-proven stage-B B-P0-2

Two frozen Citation shapes coexist and BOTH stay as-is:
- **Agent citation** (`contracts/agent_interface.py` `Citation`) = `{doc_id, section, snippet?}`.
  This is what agents actually produce (root_cause / correlation / validation). **Unchanged.**
- **Event citation** (`contracts/events.schema.json` `$defs/citation`) = `{doc_id, title, page, claim}`,
  `claim` **required**. This is what events transport. **Unchanged.**

The gap (`claim`/`page` have no live producer — the text retriever returns only
`doc_id, section, snippet`) is closed by a **transform owned by the INT.1 adapters**
(one per agent, modelled on the existing `backend/app/validation_adapter.py`), NOT by
mutating either frozen contract. The transform, canonical:

- **`claim`** = a one-sentence synthesis from the ranked cause + its snippet, formula:
  `"<cause> — per <doc title/section>"`. (Deterministic string build in the adapter; no extra LLM call.)
- **`page`** = `section → page` lookup in the corpus index; **fallback = the `section` string**
  when the index has no page (text retriever today has no page — fallback always applies until
  the visual retriever decision below lands).
- **`title`** = document title from the corpus manifest keyed by `doc_id`.
- **`doc_id`** passes through unchanged (canonical S/V/O namespace, see next entry).

**Status:** PROPOSED. Needs @aminssutt (owns the adapters) + @simerugby (owns the event
contract) to approve before INT.1 wiring. This is the P0 blocker for the live citation trail.

---

## VultronRetriever: text-now / visual-later + doc_id namespace + corpus builder  [ADOPTED for demo (text) — visual upgrade path preserved; workshop can still overturn]

**Date:** 2026-07-04 · **Author:** @vgtray (dev-backend) · **Source:** audit stage-A P1-2/3/4 (#80)

**Provisional decision — TEXT vector store for the demo.** `agents/common/retriever.py`
(text vector store, `(doc_id, section)` citations) is the **proven path**: real smoke +
143 tests green, ~200 ms. The demo ships on it.

**VISUAL retriever = documented upgrade path, NOT built.** The visual late-interaction
design in `validation/VULTRONRETRIEVER_BRIEF.md` (page images, ColQwen, MaxSim,
page-level citations, "schematic lights up" beat) is deferred and **must be revalidated at
the Vultr workshop** before any corpus work commits to it. Open workshop questions:
- Is VultronRetriever served via **Serverless Inference** or self-hosted?
- Is there a **batch / embedding endpoint** for page-image indexing?
- Is **scoring server-side** (MaxSim / `score_multi_vector`) or client-side?
- Indexing cost of 300–800 page-images as per-token vectors (the real $ risk, per stage-B B5)?

If visual wins post-workshop, `page` becomes native (feeds the Citation transform above) and
the "schematic" beat is back on; if text stays, the beat is dropped honestly.

**Canonical `doc_id` namespace = S/V/O (per `validation/DATA_MANIFEST.md`), everywhere.**
Four namespaces coexist today (S/V/O · `DOC-xxx` in data/schema.md · `eltek-…` retriever
fixtures · `etsi-…` validation fixtures). S/V/O is the primary key the frozen event fixtures
already cite (V4, S1, FIST-3-6…); the corpus manifest and every fixture manifest re-adopt it,
or citations won't resolve to a document on click.

**Corpus builder plan (for #54).** Keep all three manifest shapes intact and adapt between them:
1. `corpus_manifest.json` — **doc-level** `{doc_id, type, title, path, vendor, equipment_class, site_id, date, tags}` (loader output, data/schema.md §7).
2. **Chunking adapter** (landed: `agents/common/corpus_builder.py`) explodes each document into per-section chunks.
3. Emits `ingest_manifest` **chunk-level** rows `{doc_id, title, section, path_or_text}` consumed by `retriever.ingest_manifest`.
`DATA_MANIFEST.md` stays the human rights/sourcing table (not machine-consumed). The adapter is
the single owner of the doc→section explosion.

**Status:** ADOPTED for demo (text) — visual upgrade path preserved; the Vultr workshop can
still overturn (visual-vs-text is the one decision that can flip `page` and the corpus
indexing cost).

**2026-07-04 — chunking adapter landed** (`agents/common/corpus_builder.py`): converts the
doc-level `corpus_manifest.json` into chunk-level `ingest_manifest` rows (header/`Section N`/
numbered splitting, ~1500-char paragraph fallback), unblocking the corpus build (#54). The
retriever smoke fixtures adopted the canonical S/V/O/I namespace
(`eltek-flatpack2-om-manual`→`V2`, `site-safety-dc-power-plant`→`UFC-3-540-07`); the
Correlation/Root-Cause harness mocks follow suit.


---

## max_tokens sizing guidance  [ADOPTED]

**Date:** 2026-07-04 · **Author:** @vgtray (dev-backend) · **Source:** audit stage-A P2-5

Structured-output calls are sized **per agent** to let the model finish cleanly
(`finish_reason=stop`), not truncate. The single-call default in the client is small
(`agents/common/vultr.py`), so agents with large JSON payloads raise it explicitly:

| Agent | Constant | Value |
|-------|----------|-------|
| Correlation (plan) | `_PLAN_MAX_TOKENS` — `agents/correlation/agent.py` | 800 |
| Remediation | `_REMEDIATION_MAX_TOKENS` — `agents/remediation/agent.py` | 2000 |
| Root-Cause | `DEFAULT_MAX_TOKENS` — `agents/root_cause/agent.py` | 600 |

**Rule:** size the budget so the expected JSON completes with `finish_reason=stop`. The
client's automatic single re-prompt on invalid JSON is a **safety net, not a substitute**
for enough tokens — a payload that truncates at the cap will just truncate again. When an
agent's output grows (more ranked causes, longer procedures), bump its constant, don't lean
on the re-prompt.

---

## Cost-avoided figure = seed-derived 6800 USD  [ADOPTED — dev-backend, 2026-07-05]

**Date:** 2026-07-05 · **Author:** @vgtray (dev-backend) · **Source:** CURRENT_STATE divergence (6800 vs 4180)

The confirm-run `cost.avoided` is the value **derivable from the current seeds**:
`downtime 5.00/min × 240 min (gold restore_target) × 1.5 (gold priority_weight) + 5000 SLA
breach penalty = 6800.00 USD` (`backend/app/tools/cost.py`, `sla_params.csv`,
`cost_params.csv`). The hand-authored fixture value `4180.00` predated the flat-penalty
seed model and is retired. Applied everywhere: the deterministic CostEngine tool (already
6800, proven by `test_cost_inventory_agent`), the frozen `EVENTS.md` example, and both
`contracts/mock_stream/` fixtures now read 6800.00.
