# Arc — Agents

Arc runs seven specialized agents across two phases plus a deterministic
matchmaker. Every agent satisfies the **frozen `contracts.Agent` protocol** — a
`name` attribute and an async `run(AgentInput) -> AgentOutput` — so the
orchestrator routes them uniformly and swaps implementations without code
changes. This document gives one chapter per agent: what it consumes, what it
produces, its source files, and the design decisions that matter.

## The frozen I/O contract

Every agent is called with the same input and returns the same output shape
(`contracts/agent_interface.py`):

```python
AgentInput  = {incident_id, site_id, failure_family, context: dict}
AgentOutput = {incident_id, agent, summary, payload: dict,
               retrieved_refs: [RetrievedRef], citations: [Citation], confidence: float}
```

`context` carries the accumulated upstream findings (its inner shape is owned by
the event contract). `confidence` is load-bearing: it drives the Root-Cause
re-query gate. Two evidence types travel on the output: `RetrievedRef`
(`{doc_id, section, snippet, score?, page?}` — the full pool an agent pulled) and
`Citation` (`{doc_id, section, snippet?, page?}` — the subset actually used to
justify a claim).

### Real agents vs. adapters

The specialized agents live under `agents/`. Where an agent's native payload
differs from what the orchestrator's phase code consumes, a thin **adapter**
under `backend/app/*_adapter.py` translates the shapes and registers under the
same `name`. The orchestrator never imports a concrete agent — it only awaits the
protocol. When no Vultr key is configured, the registry keeps canned
`dummy_agents.py` stand-ins for the LLM-backed lanes so the backend still boots
(see [VULTR.md](VULTR.md) for the wiring logic).

---

## Phase 1 — Correlation

**Source:** `agents/correlation/agent.py` · **Adapter:** `backend/app/correlation_adapter.py`
· **Prompt:** `agents/correlation/prompt.md`

Correlation localizes a fault to a site + one specific piece of equipment by
reasoning over the **structured topology** (sites + equipment with `parent_id`
links), never over pixels. It is deliberately *not* a one-shot
retrieve-then-answer; it runs three visible, traced stages:

1. **Plan** — the injected Vultr client turns the fault + the site's equipment
   inventory into a localization plan (target equipment class, walk strategy,
   retrieval query). This is the model-in-the-loop planning step. With no client
   injected (offline / `--mock`), the same plan is produced deterministically
   from the alarm taxonomy (`_CODE_CLASS` → equipment class, `_FAMILY_CLASS`
   fallback). Plan call budget: `_PLAN_MAX_TOKENS = 800`.
2. **Walk** — the plan is *executed* by a deterministic descent over `parent_id`
   links: resolve the site, enter the family subtree at its root
   (`parent_id=null`), descend to the leaf-most node of the target class. **The
   topology, not the model, chooses the final `equipment_id`** — "the model
   proposes, the data disposes." This is what makes localization
   non-hallucinated. Any deviation of the planner from the taxonomy is recorded
   (`plan["deviation"]`) and logged.
3. **Retrieve** — the injected retriever corroborates the localization and yields
   the citation trail (≥1 `Citation` when consulted).

**Confidence** is composed, not guessed (`_confidence`): base 0.40, +0.25 for
localizing to a concrete node, +0.10 if unambiguous, −0.15 if it had to broaden
to the family subtree, +0.15 if retrieval corroborated — clamped to 0.05–0.97.

**Payload:** `{located_site_id, located_equipment_id, equipment_class,
reasoning_path (hop-by-hop trace), confidence, plan, retrieval_passes,
candidates}`. The adapter maps this to what phase-1 consumes:
`correlation = {site_id, equipment, equipment_class, blast_radius,
reasoning_path}` plus `added_failures`. Correlation runs offline (deterministic
plan), so it always goes real even without a Vultr key.

---

## Phase 1 — Root-Cause

**Source:** `agents/root_cause/agent.py` · **Adapter:** `backend/app/root_cause_adapter.py`
· **Prompt:** `agents/root_cause/prompt.md`

Root-Cause is the differentiator for the Vultr bar: **retrieval behind a
confidence gate**. It retrieves once, ranks candidate causes, and — only when its
own grounded confidence is below threshold — retrieves *again with an
LLM-reformulated query* before committing. If confidence is still low after the
pass budget, it stops guessing and requests the specific missing document type.

- **Gate config** (`GateConfig`): `confidence_threshold = 0.7`, `top_k = 5`,
  `max_passes = 2`, `max_tokens = 600`. The flow is exactly: pass 1 → gate →
  pass 2 (reformulated) → gate → `doc_request` if still low. The next-pass query
  is the model's `followup_query`, or a widened seed fallback.
- **Grounded confidence floor:** the gate keys on *grounded* confidence — with
  **no evidence retrieved at all, confidence is forced to 0.0** regardless of what
  the LLM claims. Ungrounded certainty is the exact failure the gate exists to
  catch (`_top_confidence(ranking) if evidence else 0.0`).
- **Citation invariant:** every ranked cause carries ≥1 citation whenever any
  evidence was retrieved — enforced structurally (a cause with no valid
  model-supplied index falls back to the top retrieved ref), not left to the LLM.
  The degenerate case (zero evidence on any pass) flags each cause `uncited`,
  floors its confidence to 0.0, and emits a mandatory `doc_request` — an
  ungrounded hypothesis never presents as a cited, confident fact.
- **The discriminant rule (sensing vs. genuine)** — from `prompt.md`: a
  sensing / measurement-path fault (telemetry itself is wrong, alarm is spurious)
  is ranked **top only when an independent field measurement contradicts the
  alarm**. Absent a field measurement, coherent telemetry (low `dc_voltage_v`
  *and* a rectifier in `fail`) points to a **real physical cause**, not a sensing
  fault. This keeps the *initial* diagnosis honest and makes the *pivot* — a
  contradicting field reading — the thing that flips it. The prompt instructs the
  model to reason in **magnitudes** and to trust the code-computed
  `measurement_interpretation` block over the raw signed number.
- **`verification_request`:** the adapter derives, from the top cause's
  `expected_measurement`, the single measurement the human loop should take. It
  targets the failure carrying the discriminating **continuous** telemetry (e.g.
  busbar `dc_voltage_v`) and uses *its* metric/point — never a boolean status
  signal encoded as 0/1 (`module_status`, `cell_active`, `backhaul_up`), which
  cannot contradict an alarm.

**Payload (native):** `{ranked_causes[{cause, confidence, citations,
expected_measurement}], retrieval_passes, doc_request}`. The adapter reshapes it
to `diagnostic = {causes[rank, cause, confidence, citations], verification_requests,
doc_request?}` and slices the evidence pool per pass into `retrievals` (each
surfaced as a `retrieval_performed` event — `pass >= 2` is the multi-retrieve
compliance proof). Root-Cause **requires** an injected Vultr client + retriever;
it cannot run offline.

---

## Human loop — Validation

**Source:** `agents/validation/agent.py` · **Adapter:** `backend/app/validation_adapter.py`

Validation sits between Phase 1 and Phase 2. A technician physically tests the
site and reports, per failure, a `real`/`false` verdict plus the real
measurement. The decision is **deterministic** (no LLM): physical measurement is
the strongest signal, verdict is the fallback.

- **`evaluate()`** returns `confirmed` when a matching measurement supports the
  fault signature (confidence 0.92) or the verdict is `real` (0.65); it returns
  `contradicted` when the measurement refutes the signature (0.90), the verdict is
  `false` (0.70), or nothing is available (0.40). A verdict that disagrees with a
  present measurement lowers confidence and is surfaced as a `verdict_measurement_conflict`.
- **Binding a measurement to a failure by metric (the adapter's key decision):**
  the load-bearing failure is the one whose *metric matches the submitted
  measurement's* — the physical quantity read at the site is what confirms or
  refutes the alarm. This keeps a −53.9 V busbar reading paired with the busbar
  `dc_voltage_v` failure, never the rectifier `module_status` failure, even when
  the `verification_request` named a different failure. Fallbacks: a
  `verdict="false"` failure, then the verification request, then highest severity.
- **Signature from the seed:** the measurement signature (`metric, unit,
  abnormal_when, threshold`) comes from the **alarm dictionary seed** — the same
  data that fired the Watchdog, so detection and validation share one source of
  truth. For `SIGNED_METRICS`, the adapter flips the seeded magnitude threshold
  to the signed field convention (`|v| < t  <=>  v > -t`).
- **Dialect translation:** the agent's `contradicted` maps to the frozen event
  value `pivot`; a `contradictions` list (`{failure_id, telemetry, measured,
  unit}`) is built for the report.

**Payload:** `{decision, matched_failure_id, rationale, verdict, measurement,
measurement_supports_fault, verdict_measurement_conflict, pivot_request?}` →
adapter adds `{result: confirmed|pivot, contradictions}`.

---

## Phase 2 — Remediation

**Source:** `agents/remediation/agent.py` · **Adapter:** `backend/app/remediation_adapter.py`

Remediation runs first in Phase 2 (after a confirm, or after a pivot
re-diagnosis). It grounds a repair procedure in the corpus and synthesizes an
**ordered, actionable procedure plus cited safety steps** with the pinned Vultr
model. −48 V DC and battery work is hazardous, so grounding is enforced, not
trusted:

- **Two targeted retrievals:** one for the repair procedure
  (`"<cause> corrective repair procedure"`), one for safety
  (`"<family> power plant servicing safety lockout tagout PPE"`). No safety
  documentation retrieved → it refuses to emit a procedure (`RemediationError`).
- **Grounding guard:** `MIN_SAFETY_STEPS = 2`. Only safety steps whose `doc_id`
  resolves to a retrieved ref are kept — a hallucinated citation is dropped, and
  fewer than two grounded safety steps raises `RemediationError`. It tolerates the
  model packing a section into the id field but still requires the base id to
  resolve to a real ref.
- **Budget:** `_REMEDIATION_MAX_TOKENS = 2000` (the largest payload in the
  system). Requires an injected Vultr client + retriever.
- **Degradation (adapter):** a `RemediationError`, `VultrError`, or timeout
  degrades to a single explicit manual-intervention step (never empty — the frozen
  schema requires `procedure.steps` `minItems >= 1`) instead of hanging the run.

**Payload (native):** `{confirmed_cause, procedure[str], safety_steps[{step,
doc_id, section}], parts_needed[str], crew_skill}`. The adapter bridges this to
the richer phase-2 procedure object `{title, steps[{n, text, citations}],
safety[{text, citations}]}` plus `parts` and `action_hints`.

---

## Phase 2 — Cost / Inventory / Dispatch

**Source:** `agents/cost_inventory/agent.py` · **Tools:** `backend/app/tools/`

The last step of Phase 2 produces the prioritized action report. It calls the
**three real backend tools** through the frozen `contracts.Tool` protocol and
**never fabricates** a price, stock line, ETA, or crew id — every such value comes
from a tool result. Each call is made explicit in the payload (`tool_calls`:
request + response), and a `totals_consistent` check verifies the report echoes
the Cost Engine's own breakdown rather than re-deriving it.

The three tools (deterministic functions over `/data` seeds):

- **Cost Engine** (`backend/app/tools/cost.py`): `repair_cost = Σ part prices + labor_rate ×
  2h + truck_roll_flat`; `avoided = downtime_cost/min × restore_target_min ×
  priority_weight + sla_breach_penalty`. On the confirm run the seeds give
  `769.04 + 2×35.73 + 325.00 = 1165.50` repair and `5.00 × 240 × 1.5 + 5000.00 =
  6800.00` avoided (`contracts/decisions.md`).
- **Inventory Lookup** (`backend/app/tools/inventory.py`): part number → real stock row
  (`in_stock`, `quantity`, `warehouse_id`, `eta_hours` = lead time when out of
  stock). An unknown part is flagged, never silently dropped.
- **Crew Dispatch** (`backend/app/tools/dispatch.py`): matches crew region == site region AND
  required skill AND `available`, lowest ETA wins; booking mutates the crew to
  `on_job` so a second dispatch exercises the conflict path (`booked=False`).
  Normalizes the agents' `power` skill to the seeded `dc_power`.

**The `suspect_part` pivot gate (orchestrator, `_suspect_part`):** the inventory
lookup is *led* by the topology-resolved catalog part so a free-text remediation
part name still resolves to real stock. This is **deterministically not applied
after a pivot** — the pivoted cause is no longer the originally-implicated
equipment, so the rectifier spare must never lead a sensing-fault report; the
lookup then follows the remediation's own parts.

**Payload:** `{cost, inventory, dispatch (consumed verbatim by the report),
tool_calls, action_report, totals_consistent}`.

### Report divergence: confirm vs. pivot

The final action report has one shape but two very different sets of numbers,
decided by the incident outcome — the demo's money shot, assembled in
`Orchestrator._assemble_report`:

- **Confirmed (genuine rectifier fault):** the `suspect_part` gate leads the
  lookup with **APR48-3G** (the Eaton -48V rectifier module, `inventory.csv`),
  found **in stock** (qty 3, warehouse `WH-PAR-EST`). Cost:
  `intervention = 769.04 + 2*35.73 + 325.00 = 1165.50`; `avoided = 6800.00` (the
  prevented outage — `5.00/min * 240 min * 1.5 + 5000.00` SLA penalty). Incident
  `outcome = resolved`.
- **Pivot (sensing / supervision fault, S2/V2):** `_suspect_part()` returns
  `None`, so no topology part leads — the inventory lookup follows the
  remediation's own part, **SP2-MU** (a Smartpack2 supervision/sensing module; the
  deterministic dummy/fallback value that `_suspect_part`'s own docstring names —
  the real Remediation agent likewise names a supervision part, never the
  rectifier spare). SP2-MU is **absent from seed stock**, so the report shows a
  clean **out-of-stock** (qty 0, `in_stock: false`) — honest procurement, never a
  fabricated match. `intervention = 396.46` (labor 71.46 + truck 325.00; the
  unstocked part contributes 0). Cost avoided is re-based to the **needless
  emergency replacement the false alarm would have triggered** — the *original*
  topology part + 2 h labor + truck roll = `769.04 + 71.46 + 325.00 = 1165.50`
  (`_assemble_report` pivot branch, from `inventory.csv` + `cost_params.csv`), not
  the outage cost — a defensible figure for catching a spurious alarm. Incident
  `outcome = downgraded`.

This is the payoff of the `suspect_part` gate: the rectifier spare can never lead
a sensing-fault report, so the two runs produce visibly different — but equally
grounded — reports from the same pipeline.

---

## Responder Matching (deterministic matchmaker)

**Source:** `agents/responder_matching/agent.py`, `agents/responder_matching/matcher.py`
· **Roster:** `data/employees.json`

After Root-Cause, the fault is routed to **one** employee to notify. This is a
pure, explainable matcher — no LLM, no network. It is *not* a frozen `agent` enum
value, so the orchestrator runs it directly in `_match_responders` (never through
`_run_agent`); its pick rides the `awaiting_field_validation` event and is
surfaced as its own `responder_matched` event. It is best-effort — a failure
degrades to no responder and never breaks the run.

- **Difficulty routing** (`CODE_DIFFICULTY`, `DIFFICULTY_TARGET`):
  `simple → 0.15` (route to the least-experienced *competent* person, so juniors
  gain experience), `medium → 0.5`, `complex → 0.9` (route to the most
  experienced).
- **Score** among eligible candidates: `0.5 × competence + 0.5 × difficulty_fit`,
  where `competence = 0.6 × skill_overlap + 0.4 × family_match` and
  `difficulty_fit = 1 − |level − target|`. `level` blends seniority and tasks
  completed (each capped). Competence is a **hard gate** — you cannot send a fibre
  tech to a rectifier fault, however junior-friendly the task.
- **Zone preference:** candidates in the site's own region win; only when nobody
  eligible and available is in-zone does the best out-of-zone responder get
  picked, flagged `out_of_zone`. `as_of` is passed in (never `date.today()`) so
  results are reproducible.

**Payload:** `{fault, difficulty, responder (chosen), notify[employee_id],
out_of_zone, escalate, alternatives}`. The orchestrator renders `chosen` +
`candidates` as the roster tightening (skill + zone `reason`), and routes the
push to the chosen technician's registered device. Not emitted on a pivot
re-diagnosis.

---

## Agent → event mapping

| Agent | Emits (via orchestrator) | Frozen `agent` enum |
|---|---|---|
| Correlation | `agent_started/completed`, `retrieval_performed` | `correlation` |
| Root-Cause | `agent_*`, `retrieval_performed` (per pass), `diagnostic_ready`, `doc_requested` | `root_cause` |
| Responder Matching | `responder_matched` | — (not a frozen enum) |
| Validation | `validation_received`, `validation_result` | `validation` |
| Remediation | `agent_*`, `retrieval_performed`, `remediation_ready` | `remediation` |
| Cost/Inventory/Dispatch | `agent_*`, `action_report_ready` | `cost_inventory_dispatch` |

Personas for the LLM-backed agents are loaded from `agents/orchestration/personas/`
(`agents/orchestration/personas.py`); each is a reviewable markdown file
versioned separately from code.
