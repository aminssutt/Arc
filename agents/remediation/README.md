# agents/remediation — Remediation agent (cited procedure + safety)

**Owner:** aminssutt · **Ticket:** AGA.2 (#29) · **Phase:** 2

Runs first in Phase 2, **only after the field CONFIRMS** the diagnosis. It grounds
a repair in the telecom corpus (VultronRetriever) and synthesizes an **ordered,
actionable procedure** + **cited safety steps** with the pinned Vultr model.

## Grounding guarantee
-48V DC / battery work is hazardous, so the agent does not trust the model to
cite honestly: it keeps only safety steps whose `doc_id` **resolves to a
retrieved corpus doc** and fails closed (`RemediationError`) if fewer than
**2** grounded safety steps remain.

## Contract
- Input: `AgentInput` — reads the confirmed cause from
  `context["findings"]["root_cause"]["top_cause"]` (or `context["top_cause"]`).
- Output: `AgentOutput` — `payload = {procedure[], safety_steps[{step,doc_id,section}],
  parts_needed[], crew_skill}`; `retrieved_refs` = evidence pool; `citations` =
  the safety sources actually used. `parts_needed` feeds the Cost/Inventory/
  Dispatch agent (#30).

## Dependencies (injected)
`VultrClient` (#24) and `VultronRetriever` (#25) are constructor args, so the
agent is unit-tested offline with fakes and needs **no API key** in tests:

```python
RemediationAgent(vultr=VultrClient(...), retriever=VultronRetriever(...))
```

## Test (from repo root)
```bash
pip install -r contracts/requirements-dev.txt
python -m pytest agents/remediation/tests -q
```
