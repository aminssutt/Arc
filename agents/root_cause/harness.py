"""Standalone CLI harness for the Root-Cause agent (issue #27 / AGV.4).

Runs the agent against a diagnostic fixture, either fully mocked (no network) or
against the real Vultr endpoint + vector store.

    # Mocked — nominal: high confidence, single pass, no doc request
    python -m agents.root_cause.harness --fixture agents/root_cause/fixtures/diag_pwr_dc_uv.json --mock

    # Mocked — forced-low: DEMONSTRATES the gate (pass 2 + doc_request)
    python -m agents.root_cause.harness --fixture agents/root_cause/fixtures/diag_forced_low.json \
        --mock --scenario forced-low

    # Real smoke: ingest the common fixtures corpus, then run for real
    source .env
    python -m agents.root_cause.harness --fixture agents/root_cause/fixtures/diag_pwr_dc_uv.json

The mocked fakes are deterministic and exercise the exact injection surface the
production clients expose (``retriever.query`` / ``vultr.structured_json``), so
the harness doubles as an executable demo of the confidence gate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from contracts.agent_interface import AgentInput, AgentOutput, RetrievedRef
from agents.root_cause.agent import GateConfig, RootCauseAgent

_COMMON_MANIFEST = "agents/common/fixtures/manifest.json"
_DEFAULT_COLLECTION = "arc_root_cause_smoke"

# Evidence the fakes return — the two ingested common fixtures, so the mocked
# runs cite the same real doc_ids the live corpus would surface.
_FAKE_ELTEK = RetrievedRef(
    doc_id="eltek-flatpack2-om-manual",
    section="3.2 DC Undervoltage Alarm",
    snippet=(
        "The rectifier module raises a DC UNDERVOLTAGE alarm when the -48V plant "
        "output falls below the low-voltage threshold. Common root causes are a "
        "failed or de-rated rectifier module, an open input breaker, or a battery "
        "string that has taken over the load during an AC mains failure."
    ),
    score=None,
)
_FAKE_SAFETY = RetrievedRef(
    doc_id="site-safety-dc-power-plant",
    section="2 Lockout/Tagout and PPE before servicing",
    snippet=(
        "Before any work on the -48V DC power plant, isolate the plant and apply "
        "lockout/tagout; verify zero energy with a meter before touching any busbar."
    ),
    score=None,
)


class _FakeRetriever:
    """Deterministic retriever: one distinct batch of refs per pass."""

    def __init__(self, batches: list[list[RetrievedRef]]) -> None:
        self._batches = batches
        self._pass = 0

    async def query(self, text: str, top_k: int = 5) -> list[RetrievedRef]:
        batch = self._batches[min(self._pass, len(self._batches) - 1)]
        self._pass += 1
        return list(batch[:top_k])


class _FakeVultr:
    """Deterministic structured_json returning canned rankings per scenario.

    ``nominal``    -> pass 1 clears the gate (top confidence 0.86).
    ``forced-low`` -> every pass stays under 0.7 and names a missing doc, so the
                      agent re-retrieves (pass 2, reformulated query) and then
                      emits a doc_request. This is the gate demonstration.
    """

    def __init__(self, scenario: str) -> None:
        self.scenario = scenario
        self.calls = 0

    async def structured_json(self, prompt, *, max_tokens: int = 600, temperature: float = 0.0) -> dict[str, Any]:
        self.calls += 1
        if self.scenario == "nominal":
            return {
                "ranked_causes": [
                    {
                        "cause": "Rectifier module failure on EQ-PAR-014-RECT-1 (module stuck in 'fail', plant on battery reserve)",
                        "confidence": 0.86,
                        "expected_measurement": "dc_plant_voltage_v",
                        "citation_refs": [0],
                    },
                    {
                        "cause": "AC mains failure with plant on battery discharge (rejected: no mains alarm)",
                        "confidence": 0.14,
                        "expected_measurement": "mains_voltage_v",
                        "citation_refs": [0],
                    },
                ],
                "followup_query": "VRLA battery discharge time to LVD on -48V string under load",
                "missing_doc": None,
            }
        # forced-low
        if self.calls == 1:
            return {
                "ranked_causes": [
                    {
                        "cause": "Rectifier module failure vs battery discharge — generic manual cannot separate them",
                        "confidence": 0.55,
                        "expected_measurement": "dc_plant_voltage_v",
                        "citation_refs": [0],
                    },
                    {
                        "cause": "AC mains failure with battery discharge",
                        "confidence": 0.30,
                        "expected_measurement": "mains_voltage_v",
                        "citation_refs": [0],
                    },
                ],
                "followup_query": "SITE-PAR-014 PWR-DC-UV historical incident ticket rectifier tripped resolution",
                "missing_doc": {
                    "description": "Site-specific historical incident ticket for SITE-PAR-014 DC undervoltage",
                    "query": "SITE-PAR-014 PWR-DC-UV historical incident resolution",
                },
            }
        return {
            "ranked_causes": [
                {
                    "cause": "Rectifier module failure (most likely) — confidence capped: no site-specific incident history in corpus",
                    "confidence": 0.58,
                    "expected_measurement": "rectifier_output_a",
                    "citation_refs": [0, 1],
                },
                {
                    "cause": "AC mains failure with battery discharge",
                    "confidence": 0.27,
                    "expected_measurement": "mains_voltage_v",
                    "citation_refs": [1],
                },
            ],
            "followup_query": "",
            "missing_doc": {
                "description": "Historical incident ticket / maintenance log for SITE-PAR-014 documenting a prior -48V undervoltage root cause",
                "query": "SITE-PAR-014 dc undervoltage incident history rectifier",
            },
        }


def _load_input(path: str) -> AgentInput:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return AgentInput.model_validate(data)


def _print_report(output: AgentOutput, elapsed_ms: float, mode: str) -> None:
    payload = output.payload
    passes = payload.get("retrieval_passes", [])
    doc_request = payload.get("doc_request")
    causes = payload.get("ranked_causes", [])

    print("=" * 72)
    print(f"ROOT-CAUSE AGENT — {mode} run")
    print("=" * 72)
    print(f"incident_id     : {output.incident_id}")
    print(f"confidence      : {output.confidence:.2f}  (gate threshold 0.70)")
    print(f"retrieval passes: {len(passes)}")
    for p in passes:
        print(f"  - pass {p['pass_number']}: refs={p['refs_count']}  query={p['query']!r}")
    print(f"gate outcome    : {'CLEARED at threshold' if output.confidence >= 0.70 else 'BELOW threshold'}")
    if doc_request is not None:
        print(f"doc_request     : {doc_request['description']}")
        print(f"                  query={doc_request['query']!r} status={doc_request['status']}")
    else:
        print("doc_request     : none")
    print("ranked_causes   :")
    for i, c in enumerate(causes, 1):
        cited = ", ".join(f"{cit['doc_id']} §{cit['section']}" for cit in c["citations"]) or "(none)"
        print(f"  {i}. [{c['confidence']:.2f}] {c['cause']}")
        print(f"       measure: {c['expected_measurement']}  |  cites: {cited}")
    print(f"total_refs      : {len(output.retrieved_refs)}")
    print(f"latency         : {elapsed_ms:.0f} ms")
    print("-" * 72)
    print("AgentOutput (model_dump_json):")
    print(output.model_dump_json(indent=2))


async def _run_mock(args: argparse.Namespace) -> AgentOutput:
    data = _load_input(args.fixture)
    if args.scenario == "forced-low":
        retriever = _FakeRetriever([[_FAKE_ELTEK], [_FAKE_SAFETY]])
    else:
        retriever = _FakeRetriever([[_FAKE_ELTEK, _FAKE_SAFETY]])
    vultr = _FakeVultr(args.scenario)
    agent = RootCauseAgent(
        vultr, retriever, config=GateConfig(confidence_threshold=args.threshold, max_tokens=args.max_tokens)
    )
    started = time.perf_counter()
    output = await agent.run(data)
    _print_report(output, (time.perf_counter() - started) * 1000, f"MOCK/{args.scenario}")
    return output


async def _run_real(args: argparse.Namespace) -> AgentOutput:
    from agents.common.vultr import VultrClient
    from agents.common.retriever import VultronRetriever

    data = _load_input(args.fixture)
    async with VultrClient() as vultr, VultronRetriever(args.collection) as retriever:
        summary = await retriever.ingest_manifest(args.ingest)
        print(f"[ingest] {args.ingest}: created={summary.created} replaced={summary.replaced} skipped={summary.skipped}")
        agent = RootCauseAgent(
            vultr, retriever, config=GateConfig(confidence_threshold=args.threshold, max_tokens=args.max_tokens)
        )
        started = time.perf_counter()
        output = await agent.run(data)
        _print_report(output, (time.perf_counter() - started) * 1000, "REAL")
        return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Root-Cause agent on a diagnostic fixture.")
    parser.add_argument("--fixture", required=True, help="Path to an AgentInput JSON fixture.")
    parser.add_argument("--mock", action="store_true", help="Run against deterministic fakes (no network).")
    parser.add_argument(
        "--scenario", choices=["nominal", "forced-low"], default="nominal",
        help="Mock scenario: 'nominal' (single pass) or 'forced-low' (pass 2 + doc_request).",
    )
    parser.add_argument("--collection", default=_DEFAULT_COLLECTION, help="Vector-store collection (real mode).")
    parser.add_argument("--ingest", default=_COMMON_MANIFEST, help="Corpus manifest to ingest (real mode).")
    parser.add_argument("--threshold", type=float, default=0.7, help="Confidence gate threshold.")
    parser.add_argument("--max-tokens", dest="max_tokens", type=int, default=600, help="Per-call max_tokens.")
    parser.add_argument("--verbose", action="store_true", help="Log per-call latency (arc.* loggers at INFO).")
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    runner = _run_mock if args.mock else _run_real
    asyncio.run(runner(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
