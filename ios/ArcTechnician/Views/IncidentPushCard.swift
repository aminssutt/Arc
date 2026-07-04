import SwiftUI

struct IncidentPushCard: View {
    let incident: IncidentPushPayload

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
            header
            siteSummary
            failuresList
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text(incident.family.rawValue)
                .font(.caption.weight(.semibold))
                .textCase(.uppercase)
                .foregroundStyle(DesignTokens.Color.accent)

            Text("Physical validation required")
                .font(.title2.weight(.semibold))
                .foregroundStyle(DesignTokens.Color.textPrimary)

            Text(incident.incidentId)
                .font(.footnote.monospaced())
                .foregroundStyle(DesignTokens.Color.textSecondary)
        }
    }

    private var siteSummary: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            Text(incident.site.name)
                .font(.headline)
                .foregroundStyle(DesignTokens.Color.textPrimary)

            if let address = incident.site.address {
                Text(address)
                    .font(.subheadline)
                    .foregroundStyle(DesignTokens.Color.textSecondary)
            }

            Text("\(incident.site.lat.formatted()), \(incident.site.lon.formatted())")
                .font(.footnote.monospaced())
                .foregroundStyle(DesignTokens.Color.textSecondary)
        }
        .padding(DesignTokens.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Color.panel)
        .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
        .overlay(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
                .stroke(DesignTokens.Color.border, lineWidth: 1)
        )
    }

    private var failuresList: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Detected failures")
                .font(.headline)
                .foregroundStyle(DesignTokens.Color.textPrimary)

            ForEach(incident.failures) { failure in
                FailureRowView(failure: failure)
            }
        }
    }
}

#Preview {
    IncidentPushCard(
        incident: IncidentPushPayload(
            incidentId: "inc-demo-confirm-001",
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
                    id: "F2",
                    code: "DC_UNDERVOLTAGE",
                    severity: .major,
                    equipment: "busbar"
                )
            ]
        )
    )
    .padding()
    .background(DesignTokens.Color.appBackground)
}
