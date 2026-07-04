# EVAL SPEC — turning "it works" into numbers a judge can't argue with

> Two tiers. Tier 1 gates the demo (must be 100%). Tier 2 produces the generalization
> number the pitch quotes. Runner touches the system only over HTTP — zero build overlap.

## Tier 1 — Demo determinism gate (Demo = 50% of score)

**Protocol:** run E1 (confirm) and E6 (pivot) **5 consecutive times each** against the
deployed stack (real backend, real push, real agents) before any judging round. Rerun
after ANY change to prompts, models, or contracts. Last green run ≥ 60 min before judging.

Pass conditions, all 5/5, per run:
1. Watchdog triggers exactly once (debounce holds; no double-fire at replay speed).
2. Correlation names the right site + equipment.
3. Root-Cause top-1 = ground truth; grid-loss correctly rejected (E1) / pivot executed (E6).
4. Push notification arrives on the phone with correct site + failure family.
5. Every citation in the report RESOLVES (doc exists in corpus, page/section supports the
   claim — spot-check 2 citations per run by opening them).
6. Report renders end-to-end; total time-to-report logged and < the demo budget
   (target: ≤ 90 s from trigger to report on screen — measure, then set the real number).
7. No hallucinated entity: every equipment name, part number, SLA figure in the report
   exists in corpus or seeded data (grep check).

**Any failure → fix → counter resets to 0/5.** That's the rule that makes it a gate.

## Tier 2 — Generalization number (the pitch's proof line)

**Protocol:** run the 16-scenario matrix (GROUND_TRUTH_SCENARIOS.md) offline, 1 pass per
scenario, after Tier-1 is first green (target: Saturday night, agents can run it while
humans sleep — venue allows overnight).

| Metric | Definition | Target to quote |
|---|---|---|
| Root-cause top-1 | agent's #1 cause == ground truth | ≥ 12/16 to quote; report the real number regardless |
| Root-cause top-3 | ground truth in ranked list | context metric |
| Citation precision | sampled citations (3/scenario) that genuinely support the claim | ≥ 90% |
| Retrieval behavior | scenarios where agent retrieved >1 time when confidence gate demanded | binary per scenario — the Vultr "agent, not RAG" proof |
| Tool correctness | cost/inventory/dispatch calls with valid args + used results | 100% on E1/E6, report rest |
| Pivot correctness | E6 + any contradicting-measurement variant: diagnosis revised, actions revised | must be 100% |
| Negative controls | N1 + N2: NO dispatch, NO P1 escalation on planned work / in-range transients | must be 2/2 |
| Hallucination count | claims with no citation and no seeded-data basis | 0 tolerated in report body |

**Scoring mechanics:** structural checks automated (JSON asserts on the report schema);
root-cause match = string/enum match against the matrix; citation support = human
spot-check (5 min/scenario) OR LLM-judge with **NemoTron via build.nvidia.com/Nebius**
(double duty: legitimate shot at the NVIDIA RTX 5080 "best NemoTron usage" bonus —
team's call, zero product-scope change).

**Honesty rules (kill-list compliant):**
- Never quote a number we didn't measure. If top-1 lands at 9/16, the pitch says 9/16 —
  paired with "every one of the 9 fully cited," which is still stronger than rivals' vibes.
- E4 stays UNSEEN during all tuning (overfit check, run once Sunday 09:00).
- RF/transport results reported as coverage-by-architecture, per taxonomy doc framing.

## Where the numbers surface (pitch integration — hand to pitch owner)

1. Demo beat: after the live run — "that wasn't a happy path: it reproduces — 5/5 this
   morning, and across a 16-scenario matrix built from real incident reports and
   standards, it lands the root cause top-1 in N/16, every claim cited."
2. Q&A armor: "how do you know it works?" has a two-tier measured answer + Grafana
   observability line ("we watch pass-rate, latency, and error rate live").
3. README section "Validation" in the public repo: matrix + numbers + corpus manifest =
   what separates product from demo (Grafana speaker's exact thesis, and judges heard
   that talk too).

## Timeline fit (no build blocking)

- **Now:** corpus manifests land (2 workflow waves running); scenarios finalized with
  pinned values.
- **After contracts freeze:** 10-line mapper JSONL→FaultEvent + thin HTTP runner
  (~1h, this lane writes it, lives under /backend or /validation — coordinate with
  simerugby on the endpoint, that's the single coordination point).
- **Sat evening:** Tier-1 first green; Tier-2 batch queued overnight.
- **Sun 09:00:** E4 unseen check; freeze numbers; hand pitch lines to vgtray.
