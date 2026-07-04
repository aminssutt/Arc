import SwiftUI

// Arc base button — Figma "Section Button", node 38:6 / component set 11:58.
// Variants: Style x Size. Disabled state follows SwiftUI's native `.disabled()` modifier
// via the `isEnabled` environment value instead of a separate State prop.
enum ArcButtonVariant {
    case primary
    case secondary
    case ghost
    case warning
    case warningSubtle

    var background: Color {
        switch self {
        case .primary: return DesignTokens.Color.accent
        case .secondary: return DesignTokens.Color.secondary
        case .ghost: return .clear
        case .warning: return DesignTokens.Color.warning
        case .warningSubtle: return DesignTokens.Color.warning.opacity(0.15)
        }
    }

    var foreground: Color {
        switch self {
        case .primary, .secondary, .warning: return DesignTokens.Color.appBackground
        case .ghost: return DesignTokens.Color.accent
        case .warningSubtle: return DesignTokens.Color.warning
        }
    }

    var border: Color? {
        switch self {
        case .ghost: return DesignTokens.Color.accent
        case .warningSubtle: return DesignTokens.Color.warning
        case .primary, .secondary, .warning: return nil
        }
    }
}

enum ArcButtonSize {
    case small
    case medium
    case large

    var height: CGFloat {
        switch self {
        case .small: return 32
        case .medium: return 42
        case .large: return 52
        }
    }

    var horizontalPadding: CGFloat {
        switch self {
        case .small: return DesignTokens.Spacing.md
        case .medium: return DesignTokens.Spacing.lg
        case .large: return DesignTokens.Spacing.xl
        }
    }

    var spacing: CGFloat {
        switch self {
        case .small, .medium: return DesignTokens.Spacing.sm
        case .large: return 10
        }
    }

    var iconSize: CGFloat {
        switch self {
        case .small: return 16
        case .medium: return 18
        case .large: return 20
        }
    }

    var font: Font {
        switch self {
        case .small: return DesignTokens.Typography.buttonSmall
        case .medium: return DesignTokens.Typography.buttonMedium
        case .large: return DesignTokens.Typography.buttonLarge
        }
    }
}

struct ArcButton: View {
    let title: String
    var variant: ArcButtonVariant = .primary
    var size: ArcButtonSize = .small
    var leadingIcon: Image?
    var trailingIcon: Image?
    let action: () -> Void

    @Environment(\.isEnabled) private var isEnabled

    var body: some View {
        Button(action: action) {
            HStack(spacing: size.spacing) {
                leadingIcon?
                    .resizable()
                    .frame(width: size.iconSize, height: size.iconSize)
                Text(title)
                    .font(size.font)
                trailingIcon?
                    .resizable()
                    .frame(width: size.iconSize, height: size.iconSize)
            }
            .padding(.horizontal, size.horizontalPadding)
            .frame(height: size.height)
            .foregroundColor(isEnabled ? variant.foreground : DesignTokens.Color.textSecondary)
            .background(isEnabled ? variant.background : DesignTokens.Color.panelRaised)
            .overlay(
                RoundedRectangle(cornerRadius: DesignTokens.Radius.sm)
                    .stroke(
                        isEnabled ? (variant.border ?? .clear) : DesignTokens.Color.border,
                        lineWidth: (isEnabled ? variant.border : DesignTokens.Color.border) == nil ? 0 : 1
                    )
            )
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.sm))
        }
        .buttonStyle(.plain)
    }
}
