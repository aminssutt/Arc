"""Event bus — builds contract envelopes, keeps history, fans out to SSE clients.

Envelope shape is FROZEN by contracts/events.schema.json:
    {seq, id, ts, incident_id, type, data}
`seq` is per-incident and gapless; `id` doubles as the SSE id for
Last-Event-ID resume (INT.5).
"""
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class EventBus:
    def __init__(self) -> None:
        self._seq: dict[str, int] = defaultdict(int)
        self.history: list[dict[str, Any]] = []
        self._subscribers: set[asyncio.Queue] = set()

    def emit(self, incident_id: str, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        self._seq[incident_id] += 1
        seq = self._seq[incident_id]
        envelope = {
            "seq": seq,
            "id": f"{incident_id}-{seq:04d}",
            "ts": _now_iso(),
            "incident_id": incident_id,
            "type": event_type,
            "data": data,
        }
        self.history.append(envelope)
        for q in list(self._subscribers):
            q.put_nowait(envelope)
        return envelope

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def replay_after(self, last_event_id: str | None) -> list[dict[str, Any]]:
        """History to resend on reconnect (Last-Event-ID semantics)."""
        if not last_event_id:
            return list(self.history)
        for i, e in enumerate(self.history):
            if e["id"] == last_event_id:
                return list(self.history[i + 1:])
        return list(self.history)

    def reset(self) -> None:
        """Demo reset (BE.11): forget incidents; live clients keep their connection."""
        self._seq.clear()
        self.history.clear()

    @staticmethod
    def sse_format(envelope: dict[str, Any]) -> str:
        payload = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)
        return f"id: {envelope['id']}\nevent: {envelope['type']}\ndata: {payload}\n\n"
