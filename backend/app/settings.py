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


def _load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Minimal stdlib .env loader (KEY=VALUE lines; '#' comments).

    Process env wins over the file; values are NEVER logged. The repo is
    PUBLIC — .env is gitignored and stays local (see .env.example). Tests
    blank the sensitive keys in conftest BEFORE importing backend modules,
    so the suite can never make paid LLM calls.

    Supports quoted multi-line values (the APNs auth key
    ``APPLE_PRIVATE_KEY_PEM`` spans several lines): when a value opens with a
    quote that is not closed on the same physical line, the following lines are
    consumed verbatim (PEM formatting preserved) until the closing quote.
    Single-line and unquoted values keep the exact previous behaviour.
    """
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    i, n = 0, len(lines)
    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        i += 1
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if value[:1] in ('"', "'"):
            quote, body = value[0], value[1:]
            if body.endswith(quote) and body != "":
                value = body[:-1]                       # closed on the same line
            else:                                       # multi-line quoted value
                collected = [body]
                while i < n:
                    nxt = lines[i]
                    i += 1
                    if nxt.rstrip().endswith(quote):
                        collected.append(nxt.rstrip()[:-1])
                        break
                    collected.append(nxt)
                value = "\n".join(collected)
        else:
            value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_bool(name: str, default: str) -> bool:
    return _env(name, default).strip().lower() in ("1", "true", "yes", "on")


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
    # `xcrun simctl push booted <file>` (macOS demo machine); 'apns' sends a real
    # token-based APNs notification (INT.7) and still writes the file so the
    # simctl/file path stays available as a fallback.
    push_mode: str = field(default_factory=lambda: _env("ARC_PUSH_MODE", "file"))
    push_bundle_id: str = field(default_factory=lambda: _env("ARC_PUSH_BUNDLE_ID", "com.arc.operator"))
    push_out_dir: Path = field(default_factory=lambda: Path(_env("ARC_PUSH_OUT_DIR", str(Path(tempfile.gettempdir()) / "arc-push-out"))))
    heartbeat_s: float = field(default_factory=lambda: float(_env("ARC_HEARTBEAT_S", "15")))
    # Agent timeout → graceful `agent_completed status=timeout`, never a crash (INT.5).
    agent_timeout_s: float = field(default_factory=lambda: float(_env("ARC_AGENT_TIMEOUT_S", "120")))
    # Auto-reset TTL: N seconds after an incident reaches a TERMINAL state the
    # backend auto-returns to a clean idle (same effect as POST /api/demo/reset),
    # so a visitor arriving long after a run sees a fresh state, not the replayed
    # final report. 0 disables it. Tests force 0 (conftest) to stay inert.
    auto_reset_s: float = field(default_factory=lambda: float(_env("ARC_AUTO_RESET_S", "600")))
    # Anti-spam push guards (INT.7): at most N pushes per incident (initial + pivot)
    # and a global minimum interval between any two pushes — a belt even if a bug
    # ever re-triggered an incident. Tests set the interval to 0.
    push_max_per_incident: int = field(default_factory=lambda: int(_env("ARC_PUSH_MAX_PER_INCIDENT", "2")))
    push_min_interval_s: float = field(default_factory=lambda: float(_env("ARC_PUSH_MIN_INTERVAL_S", "10")))
    # --- Real APNs (INT.7): token-based ES256 auth. Blank by default (repo is
    # PUBLIC); the iOS dev supplies these in the local .env. With push_mode=apns
    # AND these set, send() posts a real notification over HTTP/2 to Apple's
    # sandbox gateway. APPLE_* names are primary; APNS_* (.env.example) accepted.
    apple_team_id: str = field(default_factory=lambda: _env("APPLE_TEAM_ID", _env("APNS_TEAM_ID", "")))
    apple_key_id: str = field(default_factory=lambda: _env("APPLE_KEY_ID", _env("APNS_KEY_ID", "")))
    apple_bundle_id: str = field(default_factory=lambda: _env("APPLE_BUNDLE_ID", _env("APNS_BUNDLE_ID", _env("ARC_PUSH_BUNDLE_ID", "com.arc.operator"))))
    apple_private_key_pem: str = field(default_factory=lambda: _env("APPLE_PRIVATE_KEY_PEM", _env("APNS_AUTH_KEY", "")))
    apns_use_sandbox: bool = field(default_factory=lambda: _env_bool("APNS_USE_SANDBOX", "true"))
    # Device-token registry (POST /api/devices). Kept in a .runtime JSON file so
    # a registered iPhone survives a backend reload during rehearsals.
    device_store_path: Path = field(default_factory=lambda: Path(_env("ARC_DEVICE_STORE", str(Path(tempfile.gettempdir()) / "arc-push-out" / "devices.runtime.json"))))

    @property
    def apns_configured(self) -> bool:
        """True when all three token-auth secrets are present."""
        return bool(self.apple_team_id and self.apple_key_id and self.apple_private_key_pem)


settings = Settings()
