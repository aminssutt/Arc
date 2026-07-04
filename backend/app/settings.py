"""Backend settings — environment variables only (BE.1 acceptance).

Every knob has a sane default so `uvicorn backend.app.main:app` boots with no
setup. Secrets never live here (repo is PUBLIC): anything sensitive comes from
the local .env / process environment.
"""
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    host: str = field(default_factory=lambda: _env("ARC_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(_env("ARC_PORT", "8000")))
    # Seed data: /data per data/schema.md; falls back to backend/seed_defaults
    # (same shapes, sample rows) until DEMO.2 lands the real seed volumes.
    data_dir: Path = field(default_factory=lambda: Path(_env("ARC_DATA_DIR", str(REPO_ROOT / "data"))))
    seed_fallback_dir: Path = field(default_factory=lambda: REPO_ROOT / "backend" / "seed_defaults")
    contracts_dir: Path = field(default_factory=lambda: REPO_ROOT / "contracts")
    # Push: 'file' writes the payload JSON to push_out_dir (works everywhere and
    # doubles as the simctl input file); 'simctl' additionally shells out to
    # `xcrun simctl push booted <file>` (macOS demo machine); 'apns' is the
    # flag-gated real path (INT.7) and refuses to start unless configured.
    push_mode: str = field(default_factory=lambda: _env("ARC_PUSH_MODE", "file"))
    push_bundle_id: str = field(default_factory=lambda: _env("ARC_PUSH_BUNDLE_ID", "com.arc.technician"))
    push_out_dir: Path = field(default_factory=lambda: Path(_env("ARC_PUSH_OUT_DIR", str(Path(tempfile.gettempdir()) / "arc-push-out"))))
    heartbeat_s: float = field(default_factory=lambda: float(_env("ARC_HEARTBEAT_S", "15")))
    # Agent timeout → graceful `agent_completed status=timeout`, never a crash (INT.5).
    agent_timeout_s: float = field(default_factory=lambda: float(_env("ARC_AGENT_TIMEOUT_S", "120")))


settings = Settings()
