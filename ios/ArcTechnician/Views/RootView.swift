import SwiftUI

struct RootView: View {
    @EnvironmentObject private var pushRouter: PushNotificationRouter
    @StateObject private var backendController = BackendDemoController()
    @State private var measuredVoltage = ""

    private var displayedIncident: IncidentPushPayload {
        pushRouter.currentIncident ?? SampleIncidentFactory.payload()
    }

    var body: some View {
        NavigationStack {
            ArcNotificationScreen(
                incident: displayedIncident,
                hasLiveIncident: pushRouter.currentIncident != nil,
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
    @FocusState private var isMeasuredVoltageFocused: Bool

    let incident: IncidentPushPayload
    let hasLiveIncident: Bool
    let errorMessage: String?
    @Binding var measuredVoltage: String
    @ObservedObject var backendController: BackendDemoController

    var body: some View {
        ZStack {
            DesignTokens.Color.appBackground.ignoresSafeArea()
            DesignTokens.Color.header.ignoresSafeArea(edges: .top)

            VStack(spacing: 0) {
                header
                    .onTapGesture {
                        isMeasuredVoltageFocused = false
                    }

                ScrollView(showsIndicators: false) {
                    VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                        BuildingSituationCard(incident: incident)
                        AgentActivityCard(incident: incident)
                        RequestedActionCard(
                            incident: incident,
                            measuredVoltage: $measuredVoltage,
                            isMeasuredVoltageFocused: $isMeasuredVoltageFocused,
                            statusText: backendController.statusText,
                            submit: submitFieldTest
                        )

                        if !hasLiveIncident || errorMessage != nil {
                            DemoControls(errorMessage: errorMessage)
                        }
                    }
                    .padding(.horizontal, DesignTokens.Spacing.lg)
                    .padding(.top, DesignTokens.Spacing.lg)
                    .padding(.bottom, DesignTokens.Spacing.xl)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        isMeasuredVoltageFocused = false
                    }
                }
                .scrollDismissesKeyboard(.interactively)
            }
        }
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
        if incident.site.id.contains("-") {
            return incident.site.id.replacingOccurrences(of: "-", with: " ")
        }
        return incident.site.name
    }

    private var caseLabel: String {
        guard let failure = incident.arcPrimaryFailure else {
            return "\(incident.family.rawValue.capitalized) validation"
        }
        return "\(failure.equipment.arcTitle) \(failure.code.arcTitle)"
    }

    private func submitFieldTest() {
        guard hasLiveIncident else {
            PushNotificationRouter.shared.loadSampleIncident()
            return
        }

        backendController.submitValidation(for: incident, verdict: .real)
    }
}

private struct BuildingSituationCard: View {
    @Environment(\.colorScheme) private var colorScheme
    let incident: IncidentPushPayload

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

                    ConfidenceBadge(value: 84)
                }

                ZStack {
                    DesignTokens.Color.panelRaised

                    Image(colorScheme == .dark ? "ArcBIMDark" : "ArcBIMLight")
                        .resizable()
                        .scaledToFit()
                        .padding(.horizontal, DesignTokens.Spacing.lg)
                        .padding(.vertical, DesignTokens.Spacing.md)
                }
                .frame(maxWidth: .infinity)
                .aspectRatio(329 / 207, contentMode: .fit)
                .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
            }
        }
    }

    private var situationSubtitle: String {
        guard let failure = incident.arcPrimaryFailure else {
            return "\(incident.site.name) / Field validation"
        }
        return "\(failure.equipment.arcTitle) / \(failure.code.arcTitle) anomaly"
    }
}

private struct AgentActivityCard: View {
    let incident: IncidentPushPayload

    private var rows: [ActivityRow] {
        let family = incident.family.rawValue.capitalized
        let site = incident.site.name.components(separatedBy: " ").prefix(2).joined(separator: " ")
        let primaryFailure = incident.arcPrimaryFailure

        return [
            ActivityRow(title: "Detected \(primaryFailure?.code.arcTitle.lowercased() ?? "anomaly")", time: "03:14:02", isWarning: false),
            ActivityRow(title: "Delegated to \(family)", time: "03:15:07", isWarning: false),
            ActivityRow(title: "Retrieved \(site) schematic", time: "03:16:24", isWarning: false),
            ActivityRow(title: "Asked human for field test", time: "03:21:11", isWarning: true)
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
                                .fill(row.isWarning ? DesignTokens.Color.warning : DesignTokens.Color.activityDot)
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
                    }
                }
                .padding(DesignTokens.Spacing.lg)
                .background(DesignTokens.Color.panelRaised)
                .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
            }
        }
    }
}

private struct RequestedActionCard: View {
    let incident: IncidentPushPayload
    @Binding var measuredVoltage: String
    @FocusState.Binding var isMeasuredVoltageFocused: Bool
    let statusText: String
    let submit: () -> Void

    var body: some View {
        ArcSurfaceCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text("Requested action")
                        .font(DesignTokens.Typography.bodySmall)
                        .foregroundStyle(DesignTokens.Color.warning)

                    Text(actionTitle)
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
                        .font(DesignTokens.Typography.bodySmall)
                        .foregroundStyle(DesignTokens.Color.textPrimary)
                        .keyboardType(.decimalPad)
                        .focused($isMeasuredVoltageFocused)
                        .onSubmit {
                            isMeasuredVoltageFocused = false
                        }

                    Image(systemName: "chevron.down")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(DesignTokens.Color.textSecondary)
                }
                .padding(.horizontal, DesignTokens.Spacing.lg)
                .frame(height: 42)
                .background(DesignTokens.Color.panelRaised)
                .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm, style: .continuous))
                .onTapGesture {
                    isMeasuredVoltageFocused = true
                }

                Button(action: submit) {
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        Text("Submit field test")
                        Image(systemName: "arrow.right")
                    }
                    .font(DesignTokens.Typography.buttonMedium)
                    .frame(maxWidth: .infinity)
                    .frame(height: 42)
                }
                .buttonStyle(ArcPrimaryButtonStyle())

                HStack {
                    Button("Attach photo optional") {}
                        .font(.system(size: 13, weight: .regular))
                        .foregroundStyle(DesignTokens.Color.accent)

                    Spacer()

                    if statusText != "Backend not checked." {
                        Text(statusText)
                            .font(.caption2)
                            .foregroundStyle(DesignTokens.Color.textMuted)
                            .lineLimit(1)
                    }
                }
            }
        }
    }

    private var actionTitle: String {
        guard let failure = incident.arcPrimaryFailure else {
            return "Complete field validation"
        }

        if incident.family == .energy || failure.code.localizedCaseInsensitiveContains("voltage") {
            return "Measure \(failure.equipment.arcTitle) voltage"
        }

        return "Inspect \(failure.equipment.arcTitle)"
    }
}

private struct DemoControls: View {
    let errorMessage: String?

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            if let errorMessage {
                Text(errorMessage)
                    .font(.footnote)
                    .foregroundStyle(DesignTokens.Color.warning)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: DesignTokens.Spacing.sm) {
                Button("Load sample") {
                    PushNotificationRouter.shared.loadSampleIncident()
                }
                .buttonStyle(ArcSecondaryButtonStyle())

                Button("Test notification") {
                    PushNotificationRouter.shared.sendLocalTestNotification()
                }
                .buttonStyle(ArcSecondaryButtonStyle())
            }

            if let token = PushNotificationRouter.shared.deviceToken {
                Text(token)
                    .font(.caption2.monospaced())
                    .foregroundStyle(DesignTokens.Color.textMuted)
                    .textSelection(.enabled)
                    .lineLimit(2)
            }
        }
        .padding(.top, DesignTokens.Spacing.sm)
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

private struct ConfidenceBadge: View {
    let value: Int

    var body: some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 13, weight: .semibold))

            Text("confidence \(value)%")
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
