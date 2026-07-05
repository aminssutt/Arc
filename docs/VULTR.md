# Arc — Vultr Platform Integration

Arc is built for the Vultr track. It uses two Vultr Serverless products through a
single shared client each: **Serverless Inference** (OpenAI-compatible chat/JSON)
for the reasoning agents, and the **Vector Store API** (VultronRetriever) for
grounded retrieval. This document covers both, where every agent calls them, and
how the system meets the track's compliance bar.

## Serverless Inference

**Client:** `agents/common/vultr.py` (`VultrClient`) · **Endpoint:**
`https://api.vultrinference.com/v1` (OpenAI-compatible) · **Auth:** `Bearer`
(`VULTR_INFERENCE_API_KEY`, or `VULTR_API_KEY`).

Every reasoning agent talks to inference through this one client, which
centralizes the three things a shared credit pool needs to survive:

- **A pinned model.** The model is never hardcoded in a call. `VultrClient` reads
  the `PINNED_MODEL=` marker from `contracts/decisions.md` (single source of
  truth) at import — a missing pin fails fast and loudly. `VULTR_MODEL` overrides
  it for tests/benchmarks. The pinned model is **`deepseek-ai/DeepSeek-V4-Flash`**.
- **A concurrency cap.** A *module-level* `asyncio.Semaphore` (default **2**,
  `VULTR_MAX_CONCURRENCY`) is shared by every client instance in the process, so
  the orchestrator's fan-out stays responsive without risking 429s or draining
  the shared credit pool.
- **Retry / backoff.** Per call: `timeout=60s` (`VULTR_TIMEOUT`), **3 retries** on
  `429 / 500 / 502 / 503 / 504` and transport errors, exponential backoff + jitter
  honoring `Retry-After`.

`structured_json()` is the workhorse: it requests JSON via `response_format`
(`json_schema` when a schema is given, else `json_object`), parses the reply
(tolerating a single ```` ```json ```` fence), and **re-prompts once** if the
first reply is not a valid JSON object before raising. Latency is logged per call
(logger `arc.vultr`).

### Why DeepSeek-V4-Flash is pinned

The pin is the result of a real bench (`contracts/decisions.md`, 2026-07-04), run
through the actual client at the system's structured-output budget
(`response_format=json_object`, `max_tokens=100`, `temperature=0`, 5 calls each):

| Model | JSON ok / 5 | Median latency | Verdict |
|---|---|---|---|
| **deepseek-ai/DeepSeek-V4-Flash** | **5/5** | **1481 ms** (1336–2211 ms) | Non-reasoning, clean JSON, no stalls — **pinned** |
| zai-org/GLM-5.2-FP8 | 5/5 | 1370 ms* | Reasoning model; 4 endpoint stalls >60 s / 5 calls — tail latency unacceptable |
| moonshotai/Kimi-K2.6 | 0/5 | — | Reasoning-only; `content` stays null under budget — unusable for structured extraction |

DeepSeek-V4-Flash won on the three axes that matter for a multi-agent pipeline on
a shared pool: **reliability** (5/5 valid JSON, no timeouts), **tail latency**
(tight 1.3–2.2 s band vs. GLM's 60 s+ stalls), and **simplicity/cost**
(non-reasoning — no per-call `enable_thinking` workaround, ~27 completion tokens).
A live smoke of 5 consecutive `structured_json()` calls on the pinned model parsed
5/5 (3.0–5.4 s each); one first attempt truncated at the 100-token cap and the
client's automatic re-prompt recovered it — the JSON safety net is proven in
production. The team ran on a shared **$200** credit budget, which is why the
concurrency cap and the retry budget are deliberately conservative.

### Per-agent token budgets

Structured-output calls are sized per agent so the model finishes cleanly
(`finish_reason=stop`) rather than truncating; the re-prompt is a safety net, not
a substitute for enough tokens (`contracts/decisions.md`):

| Agent | Constant | Value |
|---|---|---|
| Correlation (plan) | `_PLAN_MAX_TOKENS` — `agents/correlation/agent.py` | 800 |
| Root-Cause (rank) | `DEFAULT_MAX_TOKENS` — `agents/root_cause/agent.py` | 600 |
| Remediation | `_REMEDIATION_MAX_TOKENS` — `agents/remediation/agent.py` | 2000 |

## Vector Store (VultronRetriever)

**Client:** `agents/common/retriever.py` (`VultronRetriever`) · **API base:**
`https://api.vultrinference.com/v1/vector_store` · **Collection:** `arc-corpus`
(`ARC_CORPUS_COLLECTION`).

Every retrieving agent (Correlation, Root-Cause, Remediation) grounds its
reasoning through this one client, which wraps the Vultr Vector Store API and
returns exactly the frozen `RetrievedRef` / `Citation` shapes. The API surface it
uses (discovered live, verified not assumed):

```
POST   /v1/vector_store                 {name}                -> {collection:{id,name}}
GET    /v1/vector_store                                       -> {collections:[…]}
POST   /v1/vector_store/{cid}/items     {content,description} -> {item:{id,…}}
GET    /v1/vector_store/{cid}/items                           -> {items:[…]}   (no content)
POST   /v1/vector_store/{cid}/search    {input}               -> {results:[{id,content}], usage}
```

Behaviors that shaped the client:

- **Collection id is derived from the name** (sanitized + truncated to ~14 chars),
  so the id returned by create is reused — the client never assumes `id == name`.
- **Metadata rides the item `description`** as compact JSON:
  `{doc_id, section, title, hash, page?}`. `hash` is a content fingerprint for
  idempotency.
- **`/search` returns results ordered by relevance but with only `id` + `content`**
  — no `description`, no numeric score. So the client resolves `doc_id` / `section`
  by joining search ids against the cached item list, enforces `top_k`
  client-side, and leaves `RetrievedRef.score = None` (the contract makes score
  optional).
- **Embedding** is server-side: the VultronRetriever family
  (`VultronRetrieverFlash-0.8B` / `Core-4.5B` / `Prime-8B`) powers `/search`; the
  Vector Store API selects/hosts it for the account.

### Idempotent, SHA-256-keyed ingestion

Ingestion is idempotent at the citation granularity `(doc_id, section)`. Each
chunk's content is fingerprinted with a **SHA-256** hash (`_content_hash`, first
16 hex chars):

- unchanged content (hash match) → **no-op** (skip);
- changed content → delete-then-insert (the API offers no native upsert);
- new pair → insert.

`ingest_manifest` fetches the existing-item list once and reports created /
replaced / skipped counts (`IngestSummary`), so re-running an ingest is safe.

### The 14-character collision guard

Because the API truncates a collection id to its first 14 characters, two
different names sharing that prefix would silently map to the same collection.
`ensure_collection` detects this (via a silent create-alias or a hard duplicate
rejection), logs a loud warning, and resolves per `on_collision`: `suffix`
(default — create a disambiguated `<name[:7]>-<sha6>` name, 14 chars unique),
`reuse` (return the colliding id, for a shared demo corpus), or `error` (raise
`CollectionCollisionError`). Team convention: names must be unique within their
first 14 characters.

## Where each agent touches Vultr

| Agent | Inference (`VultrClient`) | Retrieval (`VultronRetriever`) |
|---|---|---|
| Correlation | Plan call (`_plan`, schema, 800 tok) — **or deterministic offline** | Corroboration + citations (1 pass) |
| Root-Cause | Rank call (`_rank`, 600 tok) per pass | **Multi-pass**, confidence-gated (1–2 passes) |
| Remediation | Procedure synthesis (schema, 2000 tok) | Two targeted queries (procedure + safety) |
| Validation | — (deterministic) | — |
| Cost/Inventory/Dispatch | — (calls 3 real tools) | — |
| Responder Matching | — (deterministic matcher) | — |

The wiring lives in `backend/app/main.py` (`_build_llm_clients` /
`_wire_real_agents`): when a Vultr key is present, the shared `VultrClient` +
`VultronRetriever` are constructed and Correlation / Root-Cause / Remediation go
real; when absent, Correlation still runs (offline deterministic plan) and the
LLM-only lanes stay dummy — the backend boots either way.

## Compliance with the Vultr track

Arc is a genuine multi-agent, tool-using, multi-retrieval system — not a
single-shot RAG wrapper:

- **Multi-step agentic pipeline.** Seven specialized agents across two phases plus
  a human loop and a pivot, coordinated by a state machine — not a
  retrieve-then-answer call.
- **Retrieves more than once.** Root-Cause's confidence gate re-retrieves with an
  LLM-reformulated query when grounded confidence is below 0.7; each pass emits a
  `retrieval_performed` event, and `pass >= 2` on one incident is the
  multi-retrieve proof. Correlation and Remediation each retrieve independently.
- **Real tool calls.** The Cost/Inventory/Dispatch agent calls three real backend
  tools (Cost Engine, Inventory Lookup, Crew Dispatch) through the frozen
  `contracts.Tool` protocol, surfacing every request/response in the event
  payload — no fabricated prices, stock, or crews.
- **Not RAG-as-a-feature.** Retrieval is *behind* reasoning: a confidence gate
  decides whether to retrieve again; a grounded-confidence floor blocks ungrounded
  certainty; a missing-doc path (`doc_requested`) is emitted rather than guessing;
  and the field-truth pivot re-runs the whole diagnosis against a contradicting
  measurement.
