"""Standalone CLI harness for the Correlation agent (issue #26 / AGV.3).

    python -m agents.correlation.harness --fixture <fault.json> [--mock]

``--mock`` (the default) runs fully offline: no network, no API key. A
deterministic taxonomy planner replaces the Vultr client and a small offline
retriever supplies a canned corroborating reference so the citation trail is
demonstrated end to end.

``--no-mock`` runs the real path: it loads ``.env``, uses the pinned Vultr model
for the planning step and the real VultronRetriever for corroboration (ingesting
the shared common fixtures corpus first so the query has something to cite).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from contracts.agent_interface import AgentInput, RetrievedRef
from agents.correlation.agent import CorrelationAgent

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_MANIFEST = _REPO_ROOT / "agents" / "common" / "fixtures" / "manifest.json"
_SMOKE_COLLECTION = "arc_correlation"


# --------------------------------------------------------------------------- #
# Offline retriever (mock mode) — canned, keyword-routed corroborating refs.
# doc_ids are canonical S/V/O/I (validation/DATA_MANIFEST.md), mirroring
# agents/common/fixtures/manifest.json so mock citations look exactly like
# real-corpus ones: V2 = Eltek controller manual, UFC-3-540-07 = DC-plant
# safety, I2 = past outage report (VSWR-vs-DC misdiagnosis; RF grounding is
# offline eval R2 only).
# --------------------------------------------------------------------------- #
class _OfflineRetriever:
    async def query(self, text: str, top_k: int = 4) -> list[RetrievedRef]:
        t = text.lower()
        if "vswr" in t or "feeder" in t or "return-loss" in t or "return loss" in t:
            ref = RetrievedRef(
                doc_id="I2",
                section="VSWR vs DC misdiagnosis",
                snippet=(
                    "A high VSWR / return-loss fault on the feeder can masquerade as a "
                    "DC issue; localize to the feeder under the antenna, not the plant."
                ),
            )
        elif "batt" in t:
            ref = RetrievedRef(
                doc_id="UFC-3-540-07",
                section="Battery string autonomy",
                snippet=(
                    "A degraded VRLA battery_string shortens -48V backup autonomy; "
                    "localize to the affected string under the power plant."
                ),
            )
        else:
            ref = RetrievedRef(
                doc_id="V2",
                section="3.2 DC Undervoltage Alarm",
                snippet=(
                    "A -48V DC plant undervoltage points at the rectifier module feeding "
                    "the bus; verify rectifier output before the battery."
                ),
            )
        return [ref][:top_k]

    async def aclose(self) -> None:  # symmetry with the real retriever
        return None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_dotenv(path: Path) -> None:
    """Minimal .env loader: set KEY=VALUE lines into os.environ if not already set."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_input(fixture: Path) -> AgentInput:
    return AgentInput.model_validate(json.loads(fixture.read_text(encoding="utf-8")))


def _render(out, latency_ms: float, mode: str) -> str:
    p = out.payload
    lines = [
        "",
        f"=== Correlation agent  [{mode}]  incident={out.incident_id} ===",
        f"located_site_id      : {p.get('located_site_id')}",
        f"located_equipment_id : {p.get('located_equipment_id')}",
        f"equipment_class      : {p.get('equipment_class')}",
        f"confidence           : {out.confidence}",
        f"plan.source          : {p.get('plan', {}).get('source')}",
        f"retrieval_passes     : {p.get('retrieval_passes')}",
        "",
        "reasoning_path (topology hops):",
    ]
    for hop in p.get("reasoning_path", []):
        step = hop.get("step")
        if step == "walk_child":
            lines.append(f"  {hop['hop']}. {step}: {hop.get('from')} -> {hop.get('to')}  [{hop.get('rule')}]")
        elif step == "retrieval":
            lines.append(f"  {hop['hop']}. {step}: pass {hop.get('pass')} q={hop.get('query')!r} hits={hop.get('hits')} top={hop.get('top_doc')}")
        else:
            lines.append(f"  {hop['hop']}. {step}: {hop.get('node') or hop.get('target_class')}  [{hop.get('rule')}]")
    lines.append("")
    lines.append(f"citations ({len(out.citations)}):")
    for c in out.citations:
        lines.append(f"  - {c.doc_id} / {c.section}")
    lines.append("")
    lines.append(f"summary : {out.summary}")
    lines.append(f"latency : {latency_ms:.0f} ms")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Runners
# --------------------------------------------------------------------------- #
async def _run_mock(data: AgentInput, top_k: int):
    agent = CorrelationAgent(vultr=None, retriever=_OfflineRetriever(), top_k=top_k)
    t0 = time.perf_counter()
    out = await agent.run(data)
    return out, (time.perf_counter() - t0) * 1000


async def _run_real(data: AgentInput, top_k: int):
    _load_dotenv(_REPO_ROOT / ".env")
    from agents.common.retriever import VultronRetriever
    from agents.common.vultr import VultrClient

    vultr = VultrClient()
    retriever = VultronRetriever(_SMOKE_COLLECTION)
    try:
        try:
            summary = await retriever.ingest_manifest(_COMMON_MANIFEST)
            print(
                f"[smoke] ingested corpus into '{_SMOKE_COLLECTION}': "
                f"created={summary.created} replaced={summary.replaced} skipped={summary.skipped}",
                file=sys.stderr,
            )
        except Exception as exc:  # localization must still run without a corpus
            print(f"[smoke] corpus ingest failed ({exc}); running without retrieval corpus", file=sys.stderr)

        agent = CorrelationAgent(vultr=vultr, retriever=retriever, top_k=top_k)
        t0 = time.perf_counter()
        out = await agent.run(data)
        latency = (time.perf_counter() - t0) * 1000
    finally:
        await vultr.aclose()
        await retriever.aclose()
    return out, latency


async def _amain(args: argparse.Namespace) -> int:
    data = _load_input(Path(args.fixture))
    if args.mock:
        out, latency = await _run_mock(data, args.top_k)
        mode = "mock"
    else:
        out, latency = await _run_real(data, args.top_k)
        mode = "real"

    if args.json:
        print(json.dumps(out.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        print(_render(out, latency, mode))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agents.correlation.harness")
    parser.add_argument("--fixture", required=True, help="Path to an AgentInput JSON fixture.")
    parser.add_argument(
        "--mock",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Offline deterministic run (default). Use --no-mock for the real Vultr path.",
    )
    parser.add_argument("--top-k", type=int, default=4, help="Retriever top_k.")
    parser.add_argument("--json", action="store_true", help="Emit the raw AgentOutput as JSON.")
    args = parser.parse_args(argv)
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
