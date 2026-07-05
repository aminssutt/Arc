import SwiftUI

/// Arc visual identity — one signature colour (blue), dark, native materials.
enum ArcTheme {
    /// Signature blue for surfaces / fills (button fills, low-opacity tints).
    static let blue     = Color(red: 0.00, green: 0.471, blue: 0.682)  // #0078AE
    /// Lighter blue for foreground text/icons on dark (legible at arm's length).
    static let blueText = Color(red: 0.18, green: 0.624, blue: 0.831)  // #2E9FD4
    static let confirm  = Color(red: 0.20, green: 0.780, blue: 0.350)  // Validate / success
    static let warn     = Color(red: 1.00, green: 0.620, blue: 0.170)  // non-destructive errors
    static let bg       = Color(red: 0.05, green: 0.050, blue: 0.070)  // canvas

    static func severityColor(_ severity: String) -> Color {
        switch severity.lowercased() {
        case "critical":            return Color(red: 1.00, green: 0.27, blue: 0.23)
        case "major":               return Color(red: 1.00, green: 0.58, blue: 0.00)
        case "minor", "warning":    return Color(red: 1.00, green: 0.80, blue: 0.00)
        case "cleared":             return confirm
        default:                    return .secondary
        }
    }
}

/// Dispatch-ticket surface: dark glass, hairline border, soft lift.
struct ArcCard<Content: View>: View {
    private let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }
    var body: some View {
        content
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .strokeBorder(.white.opacity(0.08), lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.35), radius: 18, y: 10)
    }
}

/// Uppercase micro-label above a field.
struct FieldLabel: View {
    let text: String
    var body: some View {
        Text(text.uppercased())
            .font(.system(.caption2, design: .rounded).weight(.semibold))
            .tracking(0.8)
            .foregroundStyle(.secondary)
    }
}

/// Severity pill (colour-coded).
struct SeverityBadge: View {
    let severity: String
    var body: some View {
        let c = ArcTheme.severityColor(severity)
        Text(severity.uppercased())
            .font(.system(.caption2, design: .rounded).weight(.bold))
            .tracking(0.6)
            .foregroundStyle(c)
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .background(c.opacity(0.15), in: Capsule())
            .overlay(Capsule().strokeBorder(c.opacity(0.40), lineWidth: 1))
    }
}

/// Full-width, gloved-finger-tappable button content.
struct BigButtonLabel: View {
    let title: String
    let systemImage: String
    var body: some View {
        Label(title, systemImage: systemImage)
            .font(.headline)
            .frame(maxWidth: .infinity, minHeight: 32)
            .padding(.vertical, 6)
    }
}

/// Small ARC wordmark used in nav bars / headers.
struct ArcWordmark: View {
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "bolt.fill").foregroundStyle(ArcTheme.blueText).font(.subheadline)
            Text("Arc").font(.system(.headline, design: .rounded).weight(.bold))
        }
    }
}
