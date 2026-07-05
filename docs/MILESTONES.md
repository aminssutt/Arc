# Milestones — how Arc was built

Reconstructed from `git log --oneline --all`, the merged-PR record
(`gh pr list --state merged`), `contracts/decisions.md`, and
`docs/arc-pitch-scenario-3min.md`. Every PR number and date below is taken from
the real history.

**Timeline reality.** Arc is a hackathon build (RAISE Summit, Vultr track). Almost
the entire backend, agents, and contract stack landed on **2026-07-04**; the
frontend citation/control-room work, the demo-face bundle, and the iOS app
finished **overnight into 2026-07-05**. The milestones below are a logical
grouping — some tracks ran in parallel and their PR merge order interleaves
(noted where it matters), so this is not a strictly sequential wall clock.

Method of work (from `CONTRIBUTING.md` + `contracts/decisions.md`): freeze the
contracts first, build every surface against them in parallel, and flip from the
mock stream to the real backend by changing a base URL. Cross-team technical
choices are recorded, dated, and status-tagged in `contracts/decisions.md`.

---

## M1 — Roadmap, board, and frozen contracts

*2026-07-04, first ~90 minutes.*

The foundation everything else builds against: freeze the interfaces so the
backend, agents, web, and iOS can proceed without blocking each other.

- Initial scaffold, directory boundaries, and roadmap (`1657321`); repo hygiene —
  CODEOWNERS, `.gitignore`, per-directory owner READMEs (**#62**); branch
  strategy + `CONTRIBUTING.md` (**#63**); project-board links (**#60**, **#65**).
- **Frozen Agent & Tool interfaces** + `EchoAgent` + contract tests (**#66**,
  `contracts/agent_interface.py`, `contracts/echo_agent.py`).
- Telecom **seed-data schema** (**#64**, `data/schema.md`).
- **Validation lane**: corpus manifest, ground-truth scenarios, eval spec,
  retriever brief (**#67**, `validation/`).
- **FROZEN contract v1** — 14 event schemas, the push payload, the validation
  event, plus the mock SSE stream and push fixtures (**#68**,
  `contracts/events.schema.json`, `contracts/EVENTS.md`,
  `contracts/push_payload.schema.json`, `contracts/validation_event.schema.json`,
  `contracts/mock_stream/`, `contracts/push_fixtures/`).

**Decision:** the frozen event contract is the integration seam. The mock replay
server (`contracts/mock_stream/replay.py`) serves the same `/api/stream` path as
the real backend, so switching a surface from mock to live is a base-URL flip —
this is what let the web and iOS start before the backend existed.

---

## M2 — Foundations (Vultr client, retriever, core runtime)

*2026-07-04, ~13:00–13:30.*

- **Vultr inference client** — pinned model, concurrency guard, JSON safety net
  (**#71**, `agents/common/vultr.py`).
- **VultronRetriever client** — idempotent ingest, contract-shaped citations,
  unit tests (**#69**, `agents/common/retriever.py`).
- **Core backend runtime** — scaffold, watchdog, orchestrator, SSE, push, intake,
  three tools, loader, demo endpoints (**#72**, `backend/app/`).

**Decision (`contracts/decisions.md`):** one pinned model for every agent,
`deepseek-ai/DeepSeek-V4-Flash`, resolved from a machine-readable marker in
`decisions.md` (env `VULTR_MODEL` overrides). Chosen by a real 3-candidate bench
(5/5 valid JSON, 1.3–2.2 s tail vs GLM's 60 s+ stalls; Kimi-K2.6 unusable for
structured output). Concurrency is a shared module-level semaphore (default 2)
to protect the $200 shared credit pool.

---

## M3 — The specialist agents

*2026-07-04, ~13:17–13:52.*

Each agent was authored as a standalone module with an offline harness before
being wired into the live orchestrator (that wiring is M4).

- Orchestration glue + prompts/personas + offline harness (**#73**, AGA.4).
- **Validation** agent — confirm/pivot (**#70**, AGA.1; wired **#83**).
- **Remediation** agent — cited repair procedure + safety steps (**#74**, AGA.2).
- **Cost / Inventory / Dispatch** agent + action report (**#75**, AGA.3).
- **Correlation** agent — LLM plan, deterministic topology walk, auditable
  taxonomy deviation (**#84**, AGV.3).
- **Root-Cause** agent — grounded confidence gate, multi-pass retrieval,
  mandatory `doc_request` on empty evidence (**#85**, AGV.4).

The pipeline splits into **phase 1 = diagnosis** (Correlation, Root-Cause) and
**phase 2 = action** (Remediation, Cost/Inventory/Dispatch), with the human
Validation loop between them. See `docs/AGENTS.md` for each agent's contract.

---

## M4 — Orchestrator, stream, adapters (the agents go live)

*2026-07-04, ~14:00–15:30.*

Wiring the real agents into the orchestrator behind the frozen event contract,
via one adapter per agent (modelled on `backend/app/validation_adapter.py`).

- **Citation transform** (audit P0-1) + the real CID agent in the registry
  (**#86**).
- **INT.1** — the real phase-1 chain live in the orchestrator (**#89**).
- **INT.3** — the human loop + phase-2 chain live, real remediation wired
  (**#92**).
- Agent-wiring delta — `.env` autoload, a test network guard, the
  `doc_requested` event, boot-time fixture ingest, agents surfaced in `/health`
  (**#95**).
- Stage-C P0 resilience so the demo **always terminates**: phase-2 resilience
  (**#99**), the confirm run always yields a full action report (**#100**),
  correlation plan `max_tokens` 350→800 (**#98**).

**Decision (`contracts/decisions.md`):** two Citation shapes coexist and both
stay frozen — the agent citation `{doc_id, section, snippet?}` and the event
citation `{doc_id, title, page, claim}`. The gap is closed by a deterministic
transform owned by the adapters, not by mutating either contract.

---

## M5 — Corpus, final seeds, and responder matching

*2026-07-04, ~15:20–17:23.*

- **Corpus builder** — doc-level manifest → per-section chunks — plus the
  canonical **S/V/O `doc_id` namespace** and the retriever decision ADOPTED
  (**#101**, `agents/common/corpus_builder.py`).
- **DEMO.2 final scenario seeds** + canonical measurement-chain realignment
  (**#103**, `data/`).
- **Responder matching**: employee ↔ fault matching + notification decision
  (**#105**); v2 — difficulty-routed single responder + zone fallback (**#107**);
  wired into the orchestrator + notification (**#110**,
  `agents/responder_matching/`).
- Retriever collection-collision guard (**#108**); inventory match via
  topological `suspect_part` fed to the CID query (**#109**); INT.5 E2E
  hardening — phase-1 degraded terminal + mid-run resilience proofs (**#106**).

**Decision (`contracts/decisions.md`):** the demo ships on the **text** vector
retriever (proven, ~200 ms); the visual late-interaction retriever
(`validation/VULTRONRETRIEVER_BRIEF.md`) is a documented upgrade path, deferred
pending the Vultr workshop. Matching pages exactly **one** technician
(competence × difficulty-fit × zone), never a broadcast — the pitch's
"matchmaking" beat.

---

## M6 — Audits and test gates (three stages)

*Runs throughout 2026-07-04, interleaved with M4–M5.*

Quality was enforced by three audit rounds — **stage-A, stage-B, stage-C** — each
producing prioritized P0/P1/P2 fixes, tracked in `contracts/decisions.md` and the
PR titles:

- Stage-A: citation transform P0-1 (**#76** → **#86**), retriever/corpus P1
  (**#80** → **#101**), P2 safe docs subset (**#82** → **#104**); audit fixes 4A
  (python pin, wire-name docs, decisions) (**#93**) and 4B (`data/schema.md`
  reconciled to the frozen fixtures + the honest "voltage-twice" beat) (**#94**).
- Stage-B: re-proved the citation transform (B-P0-2) and flagged the visual-index
  cost risk (B5) — recorded in `decisions.md`.
- Stage-C: phase-2 resilience P0 (**#99**, **#100**), correlation `max_tokens`
  C-P1-2 (**#98**), and the final inventory-match P1 (**#109**).

The **eval gate** (`validation/EVAL_SPEC.md`) is a two-tier contract: Tier 1 is a
demo-determinism gate (E1 confirm + E6 pivot, 5/5 consecutive against the real
stack, counter resets to 0 on any failure); Tier 2 is the 16-scenario
generalization matrix quoted in the pitch. The backend carries 19 test modules
(`backend/tests/`, including `test_int1_phase1_live.py`, `test_int3_human_loop_live.py`,
`test_int5_hardening.py`, `test_phase2_resilience.py`) plus per-agent tests.

**Decision (`contracts/decisions.md`, 2026-07-05):** the confirm-run
`cost.avoided` is the **seed-derived 6800 USD**, not the retired hand-authored
`4180` — applied to the CostEngine tool, `EVENTS.md`, and both mock-stream
fixtures.

---

## M7 — Demo face (real APNs, matchmaking event, iOS app, corpus)

*Merged 2026-07-05 01:24 UTC as **PR #118** (`feat/demo-face`).*

The push toward a stage-ready end-to-end demo:

- Backend demo face — **real APNs push**, the `responder_matched` event, the
  citations API, a measurement-bound pivot, and an anti-spam watchdog
  (`91c5984`).
- Grounding **corpus** — telecom docs with pivot-vs-genuine-fault discriminant
  sections so the live pivot lands (`a36abcf`).
- The live-contract **web/iOS validation loop**, a conditional field-test modal,
  and brand assets (`a76804b`).
- The native **SwiftUI operator app** — APNs push, validate/refuse flow, theme,
  icon (`6c4e2b4`; see `docs/IOS.md`).
- Locked the **3-minute pitch scenario**, the agents spec, and architecture v2
  (`61d3776`, `docs/arc-pitch-scenario-3min.md`, `docs/arc-agents-spec.md`,
  `docs/arc-architecture-v2.mermaid`).
- Prerequisite: correlation topology read from the **live seeds** (no fixture
  drift) to unblock a real demo run (**#112**).

---

## M8 — Frontend control room + citation drill-down

*2026-07-04 20:56 UTC → 2026-07-05 05:07 UTC (**PRs #113–#116, #119, #120**).*

Note the interleave: the citation and control-room PRs (#113–#116) merged the
evening of 07-04, **before** the demo-face bundle (#118) merged early on 07-05;
the control-room restyle (#119) and the landing cleanup (#120) came after.

- Citation **drill-down L1** — clickable, resolvable, openable report sources
  (**#113**).
- Citation **drill-down L2** — page through the stack + event enrichment + the
  viewer (**#114**).
- **Next.js control room** on the live event stream + citation drill-down
  (**#115**).
- **Pitch landing** (Spline 3D) + control-room routing + matchmaking panel
  (**#116**).
- **Telecom control room** — ECU-style restyle, sky-blue theme, live agentic
  monitor + cited PDF export (**#119**).
- Landing polish — remove the "Directed, not autonomous" block from the
  agent-team section (**#120**, current `HEAD` `b9309ef`).

See `docs/FRONTEND.md` for the resulting surface (pages, the Simple/Technical
control-room views, the SSE client, the event reducer, and the citation/PDF
viewer).
