"""Arc backend app factory (BE.1). Boot: `python -m uvicorn backend.app.main:app`
from the repo root (or `python backend/run.py`). Settings via env only.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.bus import EventBus
from backend.app.dummy_agents import default_registry
from backend.app.orchestrator import Orchestrator
from backend.app.push_service import PushService
from backend.app.seeds import load_seeds
from backend.app.settings import settings
from backend.app.tools import CostEngineTool, CrewDispatchTool, InventoryLookupTool
from backend.app.validation_adapter import ValidationAgentAdapter
from backend.app.watchdog import Watchdog


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
    registry["validation"] = ValidationAgentAdapter(app.state.seeds)  # aminssutt's AGA.1
    orchestrator = Orchestrator(app.state.bus, app.state.seeds, registry,
                                push, agent_timeout_s=settings.agent_timeout_s)
    watchdog = Watchdog(app.state.seeds, orchestrator.handle_fault, orchestrator.add_failures)
    orchestrator.on_incident_closed = watchdog.incident_closed
    app.state.orchestrator = orchestrator
    app.state.watchdog = watchdog
    yield


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
            "seeds": {name: src for name, src in app.state.seeds.sources.items()},
        }

    return app


app = create_app()
