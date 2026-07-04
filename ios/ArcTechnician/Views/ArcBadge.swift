import SwiftUI

// Arc status/state pill — Figma "Section Badge", node 38:8 / component set 11:76.
enum ArcBadgeTone {
    case primary
    case secondary
    case warning
    case neutral
}

enum ArcBadgeEmphasis {
    case solid
    case subtle
}

struct ArcBadge: View {
    let label: String
    var tone: ArcBadgeTone = .primary
    var emphasis: ArcBadgeEmphasis = .solid

    private var background: Color {
        switch (tone, emphasis) {
        case (.primary, .solid): return DesignTokens.Color.accent
        case (.primary, .subtle): return DesignTokens.Color.accentSubtle
        case (.secondary, .solid): return DesignTokens.Color.secondary
        case (.secondary, .subtle): return DesignTokens.Color.secondary.opacity(0.15)
        case (.warning, .solid): return DesignTokens.Color.warning
        case (.warning, .subtle): return DesignTokens.Color.warning.opacity(0.15)
        case (.neutral, .solid): return DesignTokens.Color.textPrimary
        case (.neutral, .subtle): return DesignTokens.Color.panelRaised
        }
    }

    private var foreground: Color {
        switch (tone, emphasis) {
        case (.primary, .solid), (.secondary, .solid), (.warning, .solid), (.neutral, .solid):
            return DesignTokens.Color.appBackground
        case (.primary, .subtle): return DesignTokens.Color.accent
        case (.secondary, .subtle): return DesignTokens.Color.secondary
        case (.warning, .subtle): return DesignTokens.Color.warning
        case (.neutral, .subtle): return DesignTokens.Color.textSecondary
        }
    }

    private var border: Color? {
        switch (tone, emphasis) {
        case (.primary, .subtle): return DesignTokens.Color.accent
        case (.secondary, .subtle): return DesignTokens.Color.secondary
        case (.warning, .subtle): return DesignTokens.Color.warning
        case (.neutral, .subtle): return DesignTokens.Color.border
        default: return nil
        }
    }

    var body: some View {
        Text(label)
            .font(DesignTokens.Typography.labelSmall)
            .padding(.horizontal, DesignTokens.Spacing.md)
            .padding(.vertical, DesignTokens.Spacing.xs)
            .foregroundColor(foreground)
            .background(background)
            .overlay(
                Capsule().stroke(border ?? .clear, lineWidth: border == nil ? 0 : 1)
            )
            .clipShape(Capsule())
    }
}
