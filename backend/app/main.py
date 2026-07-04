"""Arc backend app factory (BE.1). Boot: `python -m uvicorn backend.app.main:app`
from the repo root (or `python backend/run.py`). Settings via env only.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.cost_inventory import CostInventoryDispatchAgent

from backend.app.bus import EventBus
from backend.app.dummy_agents import default_registry
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.seeds import load_seeds
from backend.app.settings import settings
from backend.app.tools import CostEngineTool, CrewDispatchTool, InventoryLookupTool
from backend.app.correlation_adapter import CorrelationAgentAdapter
from agents.responder_matching import ResponderMatchingAgent

from backend.app.remediation_adapter import RemediationAgentAdapter
from backend.app.root_cause_adapter import RootCauseAgentAdapter
from backend.app.validation_adapter import ValidationAgentAdapter
from backend.app.watchdog import Watchdog

logger = logging.getLogger("arc.backend")


def _wire_real_agents(app: FastAPI, registry: dict) -> None:
    """INT.1 (#47) + INT.3 (#49): swap dummy Vultr-backed agents for the real ones.

    Correlation runs offline (deterministic plan), so it always goes real.
    Root-Cause and Remediation REQUIRE the shared Vultr client + retriever; they
    go real only when a Vultr key is configured, so the backend boots everywhere
    (no key -> Correlation real, Root-Cause/Remediation stay dummy, never a
    crash). With the key set, both phases are zero-mock and the report carries a
    real citation trail.
    """
    seeds = app.state.seeds
    llm = _build_llm_clients()
    if llm is None:
        registry["correlation"] = CorrelationAgentAdapter(seeds=seeds)
        logger.warning("INT.1/3: no Vultr key — Correlation real (offline); Root-Cause/Remediation stay dummy")
        return
    vultr, retriever = llm
    app.state.llm_clients = llm
    registry["correlation"] = CorrelationAgentAdapter(vultr, retriever, seeds=seeds)
    registry["root_cause"] = RootCauseAgentAdapter(vultr, retriever)
    registry["remediation"] = RemediationAgentAdapter(vultr, retriever)
    logger.info("INT.1/3: wired REAL correlation + root_cause + remediation (Vultr configured)")


def _build_llm_clients():
    """(VultrClient, VultronRetriever) when a Vultr key is set, else None.

    Construction raises without a key (secret lives in the local .env only), so
    any failure degrades gracefully to the dummy path rather than breaking boot.
    """
    import os

    if not (os.getenv("VULTR_INFERENCE_API_KEY") or os.getenv("VULTR_API_KEY")):
        return None
    try:
        from agents.common.retriever import VultronRetriever
        from agents.common.vultr import VultrClient

        return VultrClient(), VultronRetriever(os.getenv("ARC_CORPUS_COLLECTION", "arc-corpus"))
    except Exception as exc:  # noqa: BLE001 - never break boot on LLM wiring
        logger.warning("INT.1: Vultr client construction failed (%s) — using dummy Root-Cause", exc)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = settings
    app.state.seeds = load_seeds(settings.data_dir, settings.seed_fallback_dir)  # BE.10: fails loud
    app.state.bus = EventBus()
    app.state.idempotency = {}

    cost = CostEngineTool(app.state.seeds)
    inventory = InventoryLookupTool(app.state.seeds)
    dispatch = CrewDispatchTool(app.state.seeds)
    app.state.dispatch_tool = dispatch
    app.state.tools = {t.name: t for t in (cost, inventory, dispatch)}

    push = PushService(app.state.bus, settings)
    registry = default_registry(cost, inventory, dispatch)
    # REAL agents replace dummies here as their lanes land (registry handoff):
    registry["validation"] = ValidationAgentAdapter(app.state.seeds)          # aminssutt's AGA.1
    registry["cost_inventory_dispatch"] = CostInventoryDispatchAgent(         # aminssutt's AGA.3
        cost, inventory, dispatch)
    registry["responder_matching"] = ResponderMatchingAgent()                # aminssutt's employee-matching (deterministic, no Vultr)
    _wire_real_agents(app, registry)  # INT.1 (#47) + INT.3 (#49): real correlation/root_cause/remediation
    llm = getattr(app.state, "llm_clients", None)
    if llm is not None:
        try:  # interim grounding until DEMO.1 lands the real corpus (idempotent re-ingest)
            summary = await llm[1].ingest_manifest("agents/common/fixtures/manifest.json")
            logger.info("retriever fixture corpus ready: %s", summary)
        except Exception as exc:  # noqa: BLE001 - retrieval then returns empty; agents degrade honestly
            logger.warning("fixture corpus ingest skipped (%s)", exc)
    orchestrator = Orchestrator(app.state.bus, app.state.seeds, registry,
                                push, agent_timeout_s=settings.agent_timeout_s)
    watchdog = Watchdog(app.state.seeds, orchestrator.handle_fault, orchestrator.add_failures)
    orchestrator.on_incident_closed = watchdog.incident_closed
    app.state.orchestrator = orchestrator
    app.state.watchdog = watchdog
    yield

    for client in getattr(app.state, "llm_clients", ()) or ():
        try:
            await client.aclose()
        except Exception:  # noqa: BLE001 - best-effort cleanup on shutdown
            pass


def create_app() -> FastAPI:
    app = FastAPI(title="Arc backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])

    from backend.app.api.routes_demo import router as demo_router
    from backend.app.api.routes_stream import router as stream_router
    from backend.app.api.routes_validation import router as validation_router
    app.include_router(stream_router)
    app.include_router(validation_router)
    app.include_router(demo_router)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "state": app.state.orchestrator.state,
            # which registry entries are real vs dummy — INT smoke check at a glance
            "agents": {name: type(agent).__name__
                       for name, agent in app.state.orchestrator.agents.items()},
            "seeds": {name: src for name, src in app.state.seeds.sources.items()},
        }

    return app


app = create_app()
