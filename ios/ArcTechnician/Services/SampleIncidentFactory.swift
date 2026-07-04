import Foundation

enum SampleIncidentFactory {
    static func payload() -> IncidentPushPayload {
        IncidentPushPayload(
            incidentId: "INC-DEMO-001",
            site: Site(
                id: "PAR-021-NORD",
                name: "Paris Nord macro site",
                lat: 48.8969,
                lon: 2.3383,
                address: "Rue de la Chapelle, 75018 Paris"
            ),
            family: .energy,
            failures: [
                DetectedFailure(
                    id: "F1",
                    code: "alarmMajorRectifier",
                    severity: .major,
                    equipment: "rectifier-2"
                ),
                DetectedFailure(
                    id: "F2",
                    code: "DC_UNDERVOLTAGE",
                    severity: .major,
                    equipment: "busbar"
                ),
                DetectedFailure(
                    id: "F3",
                    code: "HIGH_TEMP",
                    severity: .warning,
                    equipment: "cabinet"
                )
            ]
        )
    }

    static func userInfo() -> [String: Any] {
        let payload = payload()

        return [
            "incident_id": payload.incidentId,
            "site": [
                "id": payload.site.id,
                "name": payload.site.name,
                "lat": payload.site.lat,
                "lon": payload.site.lon,
                "address": payload.site.address ?? ""
            ],
            "family": payload.family.rawValue,
            "failures": payload.failures.map { failure in
                [
                    "id": failure.id,
                    "code": failure.code,
                    "severity": failure.severity.rawValue,
                    "equipment": failure.equipment
                ]
            }
        ]
    }
}
