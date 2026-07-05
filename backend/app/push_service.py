"""Push service (BE.5) — emits the contract push payload on diagnostic_ready.

Delivery modes (ARC_PUSH_MODE):
  file    — write the payload JSON to ARC_PUSH_OUT_DIR (default). The file IS the
            simctl input: on the demo Mac, `xcrun simctl push booted <file>` is
            the whole delivery step (contracts/push_fixtures/README.md).
  simctl  — file + shell out to `xcrun simctl push booted <file>` (macOS only;
            falls back to file with a warning elsewhere).
  apns    — real token-based APNs (INT.7) over HTTP/2 to the MATCHED operator's
            registered device(s); still writes the file so the simctl/file path
            stays a fallback. A missing/invalid Apple key degrades to file
            delivery (a warning, never a crash) so the backend boots everywhere.

Every payload is validated against contracts/push_payload.schema.json before
delivery — the contract is enforced at runtime, not by convention.
"""
import json
import logging
import shutil
import time
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from backend.app.bus import EventBus
from backend.app.settings import Settings

logger = logging.getLogger("arc.push")


class PushService:
    def __init__(self, bus: EventBus, settings: Settings, device_store: Any = None) -> None:
        self.bus = bus
        self.settings = settings
        self.device_store = device_store
        schema = json.loads((settings.contracts_dir / "push_payload.schema.json").read_text(encoding="utf-8"))
        self._validator = Draft202012Validator(schema)
        self._apns = self._build_apns()
        self._push_counts: dict[str, int] = {}    # incident_id -> pushes sent (anti-spam cap)
        self._last_push_ts: float = 0.0           # monotonic time of the last push (min interval)
        settings.push_out_dir.mkdir(parents=True, exist_ok=True)

    def reset(self) -> None:
        """Demo reset: clear the anti-spam counters so the next run starts clean."""
        self._push_counts.clear()
        self._last_push_ts = 0.0

    def _build_apns(self):
        """Construct the real APNs client when push_mode=apns AND the key loads.

        A missing/invalid key (or missing PyJWT) degrades to file delivery — a
        warning, never a crash — so the backend still boots (acceptance)."""
        if self.settings.push_mode != "apns":
            return None
        if not self.settings.apns_configured:
            logger.warning("ARC_PUSH_MODE=apns but APNs keys are not configured — "
                           "falling back to file delivery")
            return None
        try:
            from backend.app.apns_client import ApnsClient
            return ApnsClient(
                self.settings.apple_team_id, self.settings.apple_key_id,
                self.settings.apple_private_key_pem, self.settings.apple_bundle_id,
                use_sandbox=self.settings.apns_use_sandbox)
        except Exception as exc:  # noqa: BLE001 - bogus key / missing dep -> file fallback
            logger.warning("APNs client unavailable (%s) — falling back to file delivery",
                           exc.__class__.__name__)
            return None

    # metric -> display unit for the iPhone card reading (continuous signals only;
    # boolean status signals carry no reading).
    _METRIC_UNITS = {"dc_voltage_v": "V", "mains_voltage_v": "V", "battery_voltage_v": "V",
                     "rectifier_output_a": "A", "temp_c": "degC", "radio_temp_c": "degC",
                     "vswr_ratio": "ratio", "battery_autonomy_min": "min", "backhaul_loss_pct": "%"}

    def _reading(self, incident: dict[str, Any]) -> dict[str, Any] | None:
        """The load-bearing telemetry reading for the card (value + unit + point),
        from the failure that carries a continuous measurable quantity (busbar
        dc_voltage), never a boolean status signal. No confidence, ever."""
        for f in incident["failures"]:
            metric = f.get("metric")
            value = f.get("value")
            if metric in self._METRIC_UNITS and isinstance(value, (int, float)) and not isinstance(value, bool):
                return {"value": value, "unit": self._METRIC_UNITS[metric],
                        "point": f.get("equipment", ""), "metric": metric}
        return None

    def build_payload(self, incident: dict[str, Any]) -> dict[str, Any]:
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
        reading = self._reading(incident)
        if reading is not None:                    # additive; the iPhone card shows the reading
            payload["reading"] = reading
        return payload

    async def send(self, incident: dict[str, Any], operator_id: str | None = None) -> dict[str, Any] | None:
        incident_id = incident["id"]
        # Anti-spam belts: cap per incident (initial + optional pivot) + a global
        # minimum interval. Returns None (no push emitted) when suppressed.
        now = time.monotonic()
        count = self._push_counts.get(incident_id, 0)
        if count >= self.settings.push_max_per_incident:
            logger.warning("push suppressed: incident %s already pushed %d time(s)", incident_id, count)
            return None
        if (self._last_push_ts and self.settings.push_min_interval_s > 0
                and (now - self._last_push_ts) < self.settings.push_min_interval_s):
            logger.warning("push suppressed: within %.0fs of the last push (anti-spam) for %s",
                           self.settings.push_min_interval_s, incident_id)
            return None

        payload = self.build_payload(incident)
        errors = [e.message for e in self._validator.iter_errors(payload)]
        if errors:  # fail loud in dev — an invalid push is a contract break
            raise ValueError(f"push payload violates contract: {errors}")

        out_file = self.settings.push_out_dir / f"push_{incident_id}.json"
        out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        method = await self._deliver(out_file, payload, operator_id)

        self.bus.emit(incident_id, "push_sent", {"method": method, "payload": payload})
        self._push_counts[incident_id] = count + 1
        self._last_push_ts = now
        return payload

    async def _deliver(self, out_file: Path, payload: dict[str, Any], operator_id: str | None) -> str:
        # Real APNs first, routed to the matched operator's device(s). The written
        # file always remains as the simctl fallback.
        if self._apns is not None:
            tokens = self._target_tokens(operator_id)
            delivered = 0
            for token in tokens:
                ok, status, reason = await self._apns.send(
                    token, payload, collapse_id=payload["incident_id"])
                if ok:
                    delivered += 1
                else:
                    logger.warning("APNs delivery failed (status=%s reason=%s) for one device",
                                   status, reason)
            if delivered:
                return "apns"
            if tokens:
                logger.warning("APNs: no device accepted the push; file kept at %s", out_file)
            else:
                logger.warning("APNs mode but no device registered%s; file kept at %s",
                               f" for operator {operator_id}" if operator_id else "", out_file)

        # Contract enum is simctl|apns: 'file' mode IS the simctl path — the
        # written file is pushed with one command on the demo Mac.
        if self.settings.push_mode == "simctl" and shutil.which("xcrun"):
            try:
                subprocess.run(["xcrun", "simctl", "push", "booted", str(out_file)],
                               check=True, capture_output=True, timeout=10)
            except (subprocess.SubprocessError, OSError) as exc:
                logger.warning("simctl delivery failed (%s); payload file kept at %s", exc, out_file)
        return "simctl"

    def _target_tokens(self, operator_id: str | None) -> list[str]:
        """The matched operator's device tokens, else every registered device."""
        if self.device_store is None:
            return []
        return self.device_store.tokens_for(operator_id) or self.device_store.all_tokens()
