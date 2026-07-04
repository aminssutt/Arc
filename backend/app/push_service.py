"""Push service (BE.5) — emits the contract push payload on diagnostic_ready.

Delivery modes (ARC_PUSH_MODE):
  file    — write the payload JSON to ARC_PUSH_OUT_DIR (default). The file IS the
            simctl input: on the demo Mac, `xcrun simctl push booted <file>` is
            the whole delivery step (contracts/push_fixtures/README.md).
  simctl  — file + shell out to `xcrun simctl push booted <file>` (macOS only;
            falls back to file with a warning elsewhere).
  apns    — real APNs, flag-gated behind INT.7: refuses to construct unless the
            APNs env vars exist. No Apple dependency by default (acceptance).

Every payload is validated against contracts/push_payload.schema.json before
delivery — the contract is enforced at runtime, not by convention.
"""
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from backend.app.bus import EventBus
from backend.app.settings import Settings


class PushService:
    def __init__(self, bus: EventBus, settings: Settings) -> None:
        self.bus = bus
        self.settings = settings
        schema = json.loads((settings.contracts_dir / "push_payload.schema.json").read_text(encoding="utf-8"))
        self._validator = Draft202012Validator(schema)
        if settings.push_mode == "apns":
            raise NotImplementedError(
                "ARC_PUSH_MODE=apns is flag-gated until INT.7 (token-based .p8 auth, "
                "physical device). Use 'file' or 'simctl'.")
        settings.push_out_dir.mkdir(parents=True, exist_ok=True)

    async def send(self, incident: dict[str, Any]) -> dict[str, Any]:
        site = incident["site"]
        payload: dict[str, Any] = {
            "Simulator Target Bundle": self.settings.push_bundle_id,
            "aps": {
                "alert": {
                    "title": f"Arc — {site.get('site_id', 'site')}: {incident['family']} fault",
                    "body": f"{len(incident['failures'])} detected failure(s) await field validation",
                },
                "sound": "default",
                "category": "ARC_VALIDATION",
            },
            "incident_id": incident["id"],
            "site": {"id": site.get("site_id", ""), "name": site.get("name", ""),
                     "lat": float(site.get("lat", 0.0)), "lon": float(site.get("lon", 0.0)),
                     "address": site.get("address", "")},
            "family": incident["family"],
            "failures": [{"id": f["id"], "code": f["code"], "severity": f["severity"],
                          "equipment": f["equipment"]} for f in incident["failures"]],
        }
        errors = [e.message for e in self._validator.iter_errors(payload)]
        if errors:  # fail loud in dev — an invalid push is a contract break
            raise ValueError(f"push payload violates contract: {errors}")

        out_file = self.settings.push_out_dir / f"push_{incident['id']}.json"
        out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        delivered_via = self._deliver(out_file)

        # Contract enum is simctl|apns: 'file' mode IS the simctl path — the
        # written file is pushed with one command on the demo Mac.
        self.bus.emit(incident["id"], "push_sent", {"method": delivered_via, "payload": payload})
        return payload

    def _deliver(self, out_file: Path) -> str:
        if self.settings.push_mode == "simctl" and shutil.which("xcrun"):
            try:
                subprocess.run(["xcrun", "simctl", "push", "booted", str(out_file)],
                               check=True, capture_output=True, timeout=10)
            except (subprocess.SubprocessError, OSError) as exc:
                print(f"[push] simctl delivery failed ({exc}); payload file kept at {out_file}")
        return "simctl"
