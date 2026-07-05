"""Device-token registry (INT.7) — where the matched technician's iPhone is reached.

``POST /api/devices`` stores an APNs device token so a real push can be routed to
the person the matchmaking selected. Kept in-memory for speed and mirrored to a
small JSON file (``settings.device_store_path``) so a registered device survives a
backend reload during rehearsals. No token is ever logged.
"""
import json
import threading
from pathlib import Path
from typing import Any


class DeviceStore:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._devices: dict[str, dict[str, Any]] = {}  # token -> {platform, operator_id}
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return
        for d in data.get("devices", []):
            token = d.get("device_token")
            if token:
                self._devices[token] = {"platform": d.get("platform", "ios"),
                                        "operator_id": d.get("operator_id")}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"devices": [{"device_token": t, **meta} for t, meta in self._devices.items()]}
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def register(self, device_token: str, platform: str = "ios",
                 operator_id: str | None = None) -> None:
        with self._lock:
            self._devices[device_token] = {"platform": platform, "operator_id": operator_id}
            self._save()

    def tokens_for(self, operator_id: str | None) -> list[str]:
        """Tokens registered to one operator (empty when none / unknown operator)."""
        if not operator_id:
            return []
        with self._lock:
            return [t for t, m in self._devices.items() if m.get("operator_id") == operator_id]

    def all_tokens(self) -> list[str]:
        with self._lock:
            return list(self._devices.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._devices)
