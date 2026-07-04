"""Crew Dispatch tool (BE.9) — books a field crew over the seeded schedule.

Match: crew region == site region AND required skill in crew skills AND status
'available'; lowest ETA wins. Booking mutates the crew to 'on_job' so a second
dispatch exercises the conflict path (no crew available -> booked=False) —
acceptance criterion.
"""
from contracts import DispatchBooking, DispatchRequest

from backend.app.seeds import Seeds


class CrewDispatchTool:
    name = "crew_dispatch"
    input_schema = DispatchRequest.model_json_schema()

    def __init__(self, seeds: Seeds) -> None:
        self._seeds = seeds
        self._booked: set[str] = set()

    async def __call__(self, payload: DispatchRequest) -> DispatchBooking:
        site = self._seeds.sites.get(payload.site_id, {})
        region = site.get("region", "")
        candidates = [
            c for c in self._seeds.crew_schedule.values()
            if c["region"] == region and payload.skill in c["skills_list"] and c["status"] == "available"
        ]
        if not candidates:
            return DispatchBooking(incident_id=payload.incident_id, crew_id="",
                                   booked=False, eta_hours=None, window=None)
        crew = min(candidates, key=lambda c: c["eta_min"])
        crew["status"] = "on_job"
        self._booked.add(crew["crew_id"])
        return DispatchBooking(
            incident_id=payload.incident_id,
            crew_id=crew["crew_id"],
            booked=True,
            eta_hours=round(crew["eta_min"] / 60, 2),
            window=f"today {crew['shift_start']}-{crew['shift_end']}",
        )

    def release_all(self) -> None:
        """Demo reset support: only crews booked BY THIS TOOL go back to
        available — crews seeded as on_job stay on_job."""
        for crew_id in self._booked:
            self._seeds.crew_schedule[crew_id]["status"] = "available"
        self._booked.clear()
