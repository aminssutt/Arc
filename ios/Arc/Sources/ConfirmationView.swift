import SwiftUI

struct ConfirmationView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            content
            Spacer()
            controls
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    @ViewBuilder private var content: some View {
        switch model.submission {
        case .idle, .sending:
            VStack(spacing: 18) {
                ProgressView().controlSize(.large).tint(ArcTheme.blueText)
                Text("Sending…").font(.headline)
            }

        case let .sent(result, recap):
            statusBlock(
                icon: "checkmark.seal.fill", color: ArcTheme.confirm, bounce: true,
                title: "Sent — agent is finishing",
                message: resultCaption(result),
                recap: recap)

        case let .alreadyHandled(recap, detail):
            statusBlock(
                icon: "checkmark.circle.fill", color: ArcTheme.confirm, bounce: false,
                title: "Already handled",
                message: "This incident isn't awaiting validation anymore — it was already closed.",
                recap: recap, footnote: detail)

        case let .networkError(recap, message):
            statusBlock(
                icon: "wifi.slash", color: ArcTheme.warn, bounce: false,
                title: "Couldn't reach the backend",
                message: message,
                recap: recap)

        case let .serverError(recap, message):
            statusBlock(
                icon: "exclamationmark.octagon.fill", color: ArcTheme.warn, bounce: false,
                title: "Request rejected",
                message: message,
                recap: recap)
        }
    }

    private func statusBlock(icon: String, color: Color, bounce: Bool,
                             title: String, message: String,
                             recap: String, footnote: String? = nil) -> some View {
        VStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 54))
                .foregroundStyle(color)
                .modifier(BounceIfNeeded(active: bounce))
            VStack(spacing: 8) {
                Text(title)
                    .font(.system(.title3, design: .rounded).weight(.semibold))
                    .multilineTextAlignment(.center)
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            Label(recap, systemImage: "arrow.up.forward")
                .font(.caption.monospaced())
                .foregroundStyle(.tertiary)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(.ultraThinMaterial, in: Capsule())
            if let footnote {
                Text(footnote)
                    .font(.caption2.monospaced())
                    .foregroundStyle(.tertiary)
                    .multilineTextAlignment(.center)
            }
        }
        .padding(.horizontal, 8)
    }

    @ViewBuilder private var controls: some View {
        switch model.submission {
        case .networkError, .serverError:
            VStack(spacing: 8) {
                Button { Task { await model.retry() } } label: {
                    BigButtonLabel(title: "Retry", systemImage: "arrow.clockwise")
                }
                .buttonStyle(.borderedProminent).controlSize(.large).tint(ArcTheme.blue)
                Button("Back to diagnostic") { model.backToDiagnostic() }
                    .font(.subheadline).tint(.secondary)
            }
        case .alreadyHandled:
            Button { model.reset() } label: {
                BigButtonLabel(title: "Back to awaiting", systemImage: "antenna.radiowaves.left.and.right")
            }
            .buttonStyle(.bordered).controlSize(.large).tint(ArcTheme.blueText)
        case .sent:
            Button { model.reset() } label: {
                BigButtonLabel(title: "Done", systemImage: "checkmark")
            }
            .buttonStyle(.bordered).controlSize(.large).tint(ArcTheme.confirm)
        default:
            EmptyView()
        }
    }

    private func resultCaption(_ result: String?) -> String {
        switch result {
        case "confirmed": return "Diagnosis confirmed — the control room is writing the action report."
        case "pivot":     return "Your measurement contradicts the diagnosis — the agent is re-diagnosing live."
        default:          return "The control room is finishing the action report."
        }
    }
}

/// Applies a one-shot bounce only where it reads as success, not on error icons.
private struct BounceIfNeeded: ViewModifier {
    let active: Bool
    func body(content: Content) -> some View {
        if active {
            content.symbolEffect(.bounce, options: .nonRepeating)
        } else {
            content
        }
    }
}
