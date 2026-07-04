import SwiftUI

struct RootView: View {
    @EnvironmentObject private var pushRouter: PushNotificationRouter
    @StateObject private var backendController = BackendDemoController()
    @State private var measuredVoltage = ""

    var body: some View {
        NavigationStack {
            ArcNotificationScreen(
                incident: pushRouter.currentIncident,
                errorMessage: pushRouter.lastError,
                measuredVoltage: $measuredVoltage,
                backendController: backendController
            )
            .toolbar(.hidden, for: .navigationBar)
        }
        .tint(DesignTokens.Color.accent)
    }
}

private struct ArcNotificationScreen: View {
    @Environment(\.colorScheme) private var colorScheme
    @State private var selectedMarkerID: String?
    @State private var validationSheetShown = false

    let incident: IncidentPushPayload?
    let errorMessage: String?
    @Binding var measuredVoltage: String
    @ObservedObject var backendController: BackendDemoController

    var body: some View {
        ZStack {
            DesignTokens.Color.appBackground.ignoresSafeArea()
            DesignTokens.Color.header.ignoresSafeArea(edges: .top)

            VStack(spacing: 0) {
                header

                ScrollView(showsIndicators: false) {
                    VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                        if let incident {
                            BuildingSituationCard(
                                incident: incident,
                                markers: backendController.buildingMarkers,
                                selectedMarkerID: $selectedMarkerID
                            )
                            AgentActivityCard(
                                incident: incident,
                                liveEntries: backendController.activityEntries
                            )
                            RequestedActionCard(
                                incident: incident,
                                submitted: backendController.validationSubmitted,
                                resolved: backendController.caseResolved,
                                statusText: backendController.statusText,
                                openValidation: { validationSheetShown = true }
                            )
                        } else if !backendController.buildingMarkers.isEmpty {
                            BuildingSituationCard(
                                incident: nil,
                                markers: backendController.buildingMarkers,
                                selectedMarkerID: $selectedMarkerID
                            )
                            AgentActivityCard(
                                incident: nil,
                                liveEntries: backendController.activityEntries
                            )
                            WaitingForValidationCard(
                                statusText: backendController.statusText,
                                isConnected: backendController.isStreamConnected,
                                errorMessage: errorMessage,
                                startConfirm: { backendController.startScenario(.confirm) },
                                startPivot: { backendController.startScenario(.pivot) },
                                reset: { backendController.reset() }
                            )
                        } else {
                            WaitingForValidationCard(
                                statusText: backendController.statusText,
                                isConnected: backendController.isStreamConnected,
                                errorMessage: errorMessage,
                                startConfirm: { backendController.startScenario(.confirm) },
                                startPivot: { backendController.startScenario(.pivot) },
                                reset: { backendController.reset() }
                            )
                        }
                    }
                    .padding(.horizontal, DesignTokens.Spacing.lg)
                    .padding(.top, DesignTokens.Spacing.lg)
                    .padding(.bottom, DesignTokens.Spacing.xl)
                }
            }
        }
        .task {
            backendController.connectStream()
        }
        // The validation modal opens exactly when the human loop opens —
        // the awaiting_field_validation event right after push_sent (the same
        // beat the web shows the "Human handoff / push sent" chip). Replayed
        // history of finished cases never triggers it: their awaiting window
        // is already closed by validation_received / incident_resolved.
        .onChange(of: incident?.incidentId) { _, _ in
            presentValidationIfNeeded()
        }
        .onChange(of: backendController.awaitingValidation) { _, _ in
            presentValidationIfNeeded()
        }
        .sheet(isPresented: $validationSheetShown) {
            FieldValidationSheet(
                incident: incident,
                measuredVoltage: $measuredVoltage,
                backendController: backendController
            )
            .presentationDetents([.height(420), .large])
            .presentationDragIndicator(.visible)
        }
    }

    private func presentValidationIfNeeded() {
        guard incident != nil,
              backendController.awaitingValidation,
              !backendController.validationSubmitted,
              !validationSheetShown else { return }
        validationSheetShown = true
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    Image(colorScheme == .dark ? "ArcLogoDark" : "ArcLogoLight")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 94, height: 16, alignment: .leading)

                    Text("\(siteLabel)   /   \(caseLabel)")
                        .font(DesignTokens.Typography.bodySmall)
                        .foregroundStyle(DesignTokens.Color.textSecondary)
                        .lineLimit(1)
                        .minimumScaleFactor(0.82)
                }

                Spacer(minLength: DesignTokens.Spacing.md)

                WarningIconButton()
            }
        }
        .padding(.horizontal, DesignTokens.Spacing.lg)
        .padding(.top, DesignTokens.Spacing.md)
        .padding(.bottom, DesignTokens.Spacing.lg)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Color.header)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(DesignTokens.Color.border)
                .frame(height: 1)
        }
    }

    private var siteLabel: String {
        guard let incident else {
            return "Backend stream"
        }

        if incident.site.id.contains("-") {
            return incident.site.id.replacingOccurrences(of: "-", with: " ")
        }
        return incident.site.name
    }

    private var caseLabel: String {
        guard let incident else {
            return "Waiting for validation request"
        }

        guard let failure = incident.arcPrimaryFailure else {
            return "\(incident.family.rawValue.capitalized) validation"
        }
        return "\(failure.equipment.arcTitle) \(failure.code.arcTitle)"
    }

}

private struct WaitingForValidationCard: View {
    let statusText: String
    let isConnected: Bool
    let errorMessage: String?
    let startConfirm: () -> Void
    let startPivot: () -> Void
    let reset: () -> Void

    var body: some View {
        ArcSurfaceCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text("Waiting for validation request")
                        .font(DesignTokens.Typography.h5)
                        .foregroundStyle(DesignTokens.Color.textPrimary)

                    Text("Keep this screen open. The incident card appears when the backend emits push_sent.")
                        .font(DesignTokens.Typography.bodySmall)
                        .foregroundStyle(DesignTokens.Color.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                HStack(spacing: DesignTokens.Spacing.sm) {
                    Circle()
                        .fill(isConnected ? DesignTokens.Color.activityDot : DesignTokens.Color.warning)
                        .frame(width: 7, height: 7)

                    Text(statusText)
                        .font(DesignTokens.Typography.bodySmall)
                        .foregroundStyle(DesignTokens.Color.textPrimary)
                        .lineLimit(2)
                }
                .padding(DesignTokens.Spacing.lg)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(DesignTokens.Color.panelRaised)
                .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))

                VStack(spacing: DesignTokens.Spacing.sm) {
                    Button(action: startConfirm) {
                        HStack(spacing: DesignTokens.Spacing.sm) {
                            Text("Start validation signal")
                            Image(systemName: "arrow.right")
                        }
                        .font(DesignTokens.Typography.buttonMedium)
                        .frame(maxWidth: .infinity)
                        .frame(height: 42)
                    }
                    .buttonStyle(ArcPrimaryButtonStyle())

                    HStack(spacing: DesignTokens.Spacing.sm) {
                        Button("Start pivot") {
                            startPivot()
                        }
                        .buttonStyle(ArcSecondaryButtonStyle())

                        Button("Reset") {
                            reset()
                        }
                        .buttonStyle(ArcSecondaryButtonStyle())
                    }
                }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.footnote)
                        .foregroundStyle(DesignTokens.Color.warning)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }
}

private struct BuildingSituationCard: View {
    @Environment(\.colorScheme) private var colorScheme
    let incident: IncidentPushPayload?
    let markers: [BuildingEvidenceMarker]
    @Binding var selectedMarkerID: String?

    var body: some View {
        ArcSurfaceCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                        Text("Building Situation")
                            .font(DesignTokens.Typography.h5)
                            .foregroundStyle(DesignTokens.Color.textPrimary)

                        Text(situationSubtitle)
                            .font(DesignTokens.Typography.bodySmall)
                            .foregroundStyle(DesignTokens.Color.textSecondary)
                    }

                    ValidationBadge(text: incident?.arcPrimaryFailure?.severity.rawValue ?? "live")
                }

                ZStack {
                    DesignTokens.Color.panelRaised

                    Image(colorScheme == .dark ? "ArcBIMDark" : "ArcBIMLight")
                        .resizable()
                        .scaledToFit()
                        .padding(.horizontal, DesignTokens.Spacing.lg)
                        .padding(.vertical, DesignTokens.Spacing.md)

                    GeometryReader { proxy in
                        ForEach(markers) { marker in
                            BuildingMarkerButton(
                                marker: marker,
                                selected: selectedMarkerID == marker.id
                            ) {
                                selectedMarkerID = selectedMarkerID == marker.id ? nil : marker.id
                            }
                            .position(
                                x: proxy.size.width * marker.x / 100,
                                y: proxy.size.height * marker.y / 100
                            )
                        }
                    }
                }
                .frame(maxWidth: .infinity)
                .aspectRatio(329 / 207, contentMode: .fit)
                .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))

                if let selectedMarker {
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        Text(selectedMarker.id)
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(DesignTokens.Color.onPrimary)
                            .padding(.horizontal, DesignTokens.Spacing.sm)
                            .frame(height: 22)
                            .background(markerColor(for: selectedMarker.tone))
                            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))

                        VStack(alignment: .leading, spacing: 2) {
                            Text(selectedMarker.title)
                                .font(DesignTokens.Typography.bodySmall.weight(.medium))
                                .foregroundStyle(DesignTokens.Color.textPrimary)
                                .lineLimit(1)
                            Text(selectedMarker.meta)
                                .font(.caption)
                                .foregroundStyle(DesignTokens.Color.textMuted)
                                .lineLimit(1)
                        }

                        Spacer(minLength: 0)
                    }
                    .padding(DesignTokens.Spacing.md)
                    .background(DesignTokens.Color.panelRaised)
                    .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
                }
            }
        }
    }

    private var situationSubtitle: String {
        guard let incident else {
            return "Live backend stream / incoming evidence"
        }

        guard let failure = incident.arcPrimaryFailure else {
            return "\(incident.site.name) / Field validation"
        }
        return "\(failure.equipment.arcTitle) / \(failure.code.arcTitle) anomaly"
    }

    private var selectedMarker: BuildingEvidenceMarker? {
        guard let selectedMarkerID else { return nil }
        return markers.first { $0.id == selectedMarkerID }
    }
}

private struct BuildingMarkerButton: View {
    let marker: BuildingEvidenceMarker
    let selected: Bool
    let action: () -> Void

    @State private var pulse = false

    var body: some View {
        Button(action: action) {
            ZStack {
                Circle()
                    .fill(markerColor(for: marker.tone))
                    .frame(width: 28, height: 28)
                    .scaleEffect(pulse ? 2.25 : 1)
                    .opacity(pulse ? 0 : 0.45)

                Circle()
                    .fill(markerColor(for: marker.tone))
                    .frame(width: 28, height: 28)
                    .overlay {
                        Text(String(marker.id.prefix(2)))
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(DesignTokens.Color.onPrimary)
                    }
                    .overlay {
                        if selected {
                            Circle()
                                .stroke(DesignTokens.Color.textPrimary, lineWidth: 2)
                                .frame(width: 34, height: 34)
                        }
                    }
            }
            .frame(width: 54, height: 54)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(marker.id) \(marker.title)")
        .onAppear {
            pulse = false
            withAnimation(.easeOut(duration: 1.8).repeatForever(autoreverses: false)) {
                pulse = true
            }
        }
    }
}

private func markerColor(for tone: BuildingEvidenceTone) -> Color {
    switch tone {
    case .primary, .primarySubtle:
        return DesignTokens.Color.accent
    case .warning:
        return DesignTokens.Color.warning
    case .secondary:
        return DesignTokens.Color.secondary
    }
}

private struct AgentActivityCard: View {
    let incident: IncidentPushPayload?
    /// Live rows derived from the SSE stream; the push-fixture fallback below
    /// keeps the card meaningful when only a simctl push arrived.
    let liveEntries: [AgentActivityEntry]

    private var rows: [ActivityRow] {
        if !liveEntries.isEmpty {
            return liveEntries.map { entry in
                ActivityRow(
                    title: entry.title,
                    time: entry.time,
                    isWarning: entry.tone == .warning,
                    isResolved: entry.tone == .resolved
                )
            }
        }

        guard let incident else { return [] }
        let family = incident.family.rawValue.capitalized
        let site = incident.site.name.components(separatedBy: " ").prefix(2).joined(separator: " ")
        let primaryFailure = incident.arcPrimaryFailure

        return [
            ActivityRow(title: "Detected \(primaryFailure?.code.arcTitle.lowercased() ?? "anomaly")", time: "03:14:02", isWarning: false, isResolved: false),
            ActivityRow(title: "Delegated to \(family)", time: "03:15:07", isWarning: false, isResolved: false),
            ActivityRow(title: "Retrieved \(site) schematic", time: "03:16:24", isWarning: false, isResolved: false),
            ActivityRow(title: "Asked human for field test", time: "03:21:11", isWarning: true, isResolved: false)
        ]
    }

    var body: some View {
        ArcSurfaceCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                Text("Agent activity")
                    .font(DesignTokens.Typography.h5)
                    .foregroundStyle(DesignTokens.Color.textPrimary)

                VStack(spacing: DesignTokens.Spacing.sm) {
                    ForEach(rows) { row in
                        HStack(spacing: DesignTokens.Spacing.sm) {
                            Circle()
                                .fill(dotColor(for: row))
                                .frame(width: 7, height: 7)

                            Text(row.title)
                                .font(DesignTokens.Typography.bodySmall)
                                .foregroundStyle(DesignTokens.Color.textPrimary)
                                .lineLimit(1)
                                .minimumScaleFactor(0.82)

                            Spacer(minLength: DesignTokens.Spacing.sm)

                            Text(row.time)
                                .font(DesignTokens.Typography.bodySmall.weight(.medium))
                                .foregroundStyle(row.isWarning ? DesignTokens.Color.warning : DesignTokens.Color.textSecondary)
                        }
                        .transition(.opacity.combined(with: .move(edge: .bottom)))
                    }
                }
                .padding(DesignTokens.Spacing.lg)
                .background(DesignTokens.Color.panelRaised)
                .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
                .animation(.easeOut(duration: 0.35), value: rows.map(\.title))
            }
        }
    }

    private func dotColor(for row: ActivityRow) -> Color {
        if row.isResolved { return DesignTokens.Color.secondary }
        if row.isWarning { return DesignTokens.Color.warning }
        return DesignTokens.Color.activityDot
    }
}

private struct RequestedActionCard: View {
    let incident: IncidentPushPayload
    let submitted: Bool
    let resolved: Bool
    let statusText: String
    let openValidation: () -> Void

    var body: some View {
        ArcSurfaceCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text(submitted ? "Field test" : "Requested action")
                        .font(DesignTokens.Typography.bodySmall)
                        .foregroundStyle(submitted ? DesignTokens.Color.secondary : DesignTokens.Color.warning)

                    Text(submitted ? "Field test submitted" : incident.arcActionTitle)
                        .font(DesignTokens.Typography.h5)
                        .foregroundStyle(DesignTokens.Color.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(subtitle)
                        .font(DesignTokens.Typography.bodySmall)
                        .foregroundStyle(DesignTokens.Color.textMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if submitted {
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        Image(systemName: resolved ? "checkmark.circle.fill" : "hourglass")
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundStyle(DesignTokens.Color.secondary)

                        Text(resolved ? "Incident resolved — action report archived." : statusText)
                            .font(DesignTokens.Typography.bodySmall)
                            .foregroundStyle(DesignTokens.Color.textPrimary)
                            .lineLimit(2)
                    }
                    .padding(DesignTokens.Spacing.lg)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(DesignTokens.Color.panelRaised)
                    .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
                } else {
                    Button(action: openValidation) {
                        HStack(spacing: DesignTokens.Spacing.sm) {
                            Text("Enter field measurement")
                            Image(systemName: "arrow.right")
                        }
                        .font(DesignTokens.Typography.buttonMedium)
                        .frame(maxWidth: .infinity)
                        .frame(height: 42)
                    }
                    .buttonStyle(ArcPrimaryButtonStyle())
                }
            }
        }
    }

    private var subtitle: String {
        submitted
            ? "The validation agent is scoring your verdict. Remediation continues automatically."
            : "Use insulated gloves. Enter the measured voltage before remediation proceeds."
    }
}

/// Conditional validation modal — presented only while the backend is
/// waiting on the human loop, never pinned to the layout.
private struct FieldValidationSheet: View {
    @Environment(\.dismiss) private var dismiss
    @FocusState private var voltageFocused: Bool
    @State private var verdict: ValidationVerdict = .real
    @State private var submitting = false

    let incident: IncidentPushPayload?
    @Binding var measuredVoltage: String
    @ObservedObject var backendController: BackendDemoController

    var body: some View {
        ZStack {
            DesignTokens.Color.panel.ignoresSafeArea()

            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text("Requested action")
                        .font(DesignTokens.Typography.bodySmall)
                        .foregroundStyle(DesignTokens.Color.warning)

                    Text(incident?.arcActionTitle ?? "Complete field validation")
                        .font(DesignTokens.Typography.h5)
                        .foregroundStyle(DesignTokens.Color.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)

                    Text("Use insulated gloves. Enter the measured voltage before remediation proceeds.")
                        .font(DesignTokens.Typography.bodySmall)
                        .foregroundStyle(DesignTokens.Color.textMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }

                HStack(spacing: DesignTokens.Spacing.sm) {
                    TextField("Enter measured voltage", text: $measuredVoltage)
                        .font(DesignTokens.Typography.body)
                        .foregroundStyle(DesignTokens.Color.textPrimary)
                        .keyboardType(.decimalPad)
                        .focused($voltageFocused)

                    Text("V")
                        .font(DesignTokens.Typography.bodySmall.weight(.medium))
                        .foregroundStyle(DesignTokens.Color.textSecondary)
                }
                .padding(.horizontal, DesignTokens.Spacing.lg)
                .frame(height: 46)
                .background(DesignTokens.Color.panelRaised)
                .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))

                HStack(spacing: DesignTokens.Spacing.sm) {
                    verdictButton(.real, label: "Real fault")
                    verdictButton(.falseAlarm, label: "False alarm")
                }

                Button(action: submit) {
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        if submitting {
                            ProgressView()
                                .tint(DesignTokens.Color.onPrimary)
                        }
                        Text(submitting ? "Submitting…" : "Submit field test")
                        if !submitting {
                            Image(systemName: "arrow.right")
                        }
                    }
                    .font(DesignTokens.Typography.buttonMedium)
                    .frame(maxWidth: .infinity)
                    .frame(height: 46)
                }
                .buttonStyle(ArcPrimaryButtonStyle())
                .disabled(submitting || incident == nil)

                Button("Attach photo optional") {}
                    .font(.system(size: 13, weight: .regular))
                    .foregroundStyle(DesignTokens.Color.accent)

                Spacer(minLength: 0)
            }
            .padding(DesignTokens.Spacing.xl)
        }
        .onAppear {
            voltageFocused = true
        }
    }

    private func verdictButton(_ value: ValidationVerdict, label: String) -> some View {
        Button {
            verdict = value
        } label: {
            Text(label)
                .font(DesignTokens.Typography.buttonSmall)
                .frame(maxWidth: .infinity)
                .frame(height: 38)
        }
        .foregroundStyle(verdict == value ? DesignTokens.Color.accent : DesignTokens.Color.textSecondary)
        .background(verdict == value ? DesignTokens.Color.accentSubtle : DesignTokens.Color.panelRaised)
        .overlay {
            RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous)
                .stroke(verdict == value ? DesignTokens.Color.accent : DesignTokens.Color.border, lineWidth: 1)
        }
        .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
    }

    private func submit() {
        guard !submitting else { return }
        submitting = true
        voltageFocused = false

        backendController.submitValidation(
            for: incident,
            verdict: verdict,
            measuredVoltage: Double(measuredVoltage.replacingOccurrences(of: ",", with: "."))
        ) { success in
            submitting = false
            if success {
                dismiss()
            }
        }
    }
}

private extension IncidentPushPayload {
    var arcActionTitle: String {
        guard let failure = arcPrimaryFailure else {
            return "Complete field validation"
        }

        if family == .energy || failure.code.localizedCaseInsensitiveContains("voltage") {
            return "Measure \(failure.equipment.arcTitle) voltage"
        }

        return "Inspect \(failure.equipment.arcTitle)"
    }
}

private struct ArcSurfaceCard<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(DesignTokens.Spacing.lg)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(DesignTokens.Color.panel)
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.lg, style: .continuous))
    }
}

private struct ValidationBadge: View {
    let text: String

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 13, weight: .semibold))

            Text(text.arcTitle)
                .font(DesignTokens.Typography.buttonSmall)
        }
        .foregroundStyle(DesignTokens.Color.warning)
        .padding(.horizontal, DesignTokens.Spacing.md)
        .frame(height: 32)
        .background(DesignTokens.Color.warningSubtle)
        .overlay {
            RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous)
                .stroke(DesignTokens.Color.warningBorder, lineWidth: 1)
        }
        .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
    }
}

private struct WarningIconButton: View {
    var body: some View {
        Button(action: {}) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 15, weight: .semibold))
                .frame(width: 38, height: 38)
        }
        .foregroundStyle(DesignTokens.Color.warning)
        .background(DesignTokens.Color.warningSubtle)
        .overlay {
            RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous)
                .stroke(DesignTokens.Color.warningBorder, lineWidth: 1)
        }
        .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
    }
}

private struct ArcPrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(DesignTokens.Color.onPrimary)
            .background(DesignTokens.Color.accent.opacity(configuration.isPressed ? 0.72 : 1))
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
    }
}

private struct ArcSecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(DesignTokens.Typography.buttonSmall)
            .foregroundStyle(DesignTokens.Color.textPrimary)
            .frame(maxWidth: .infinity)
            .frame(height: 38)
            .background(DesignTokens.Color.panelRaised.opacity(configuration.isPressed ? 0.7 : 1))
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
    }
}

private struct ActivityRow: Identifiable {
    let id = UUID()
    let title: String
    let time: String
    let isWarning: Bool
    let isResolved: Bool
}

private extension IncidentPushPayload {
    var arcPrimaryFailure: DetectedFailure? {
        failures.first { failure in
            failure.code.localizedCaseInsensitiveContains("voltage")
        } ?? failures.first
    }
}

private extension String {
    var arcTitle: String {
        let separated = reduce(into: "") { result, character in
            if character == "_" || character == "-" {
                result.append(" ")
                return
            }

            if character.isUppercase, result.last?.isLetter == true, result.last?.isLowercase == true {
                result.append(" ")
            }

            result.append(character)
        }

        return separated
            .split(separator: " ")
            .map { word in
                word.prefix(1).uppercased() + word.dropFirst().lowercased()
            }
            .joined(separator: " ")
    }
}

#Preview("Light") {
    RootView()
        .environmentObject(PushNotificationRouter.shared)
        .preferredColorScheme(.light)
}

#Preview("Dark") {
    RootView()
        .environmentObject(PushNotificationRouter.shared)
        .preferredColorScheme(.dark)
}
