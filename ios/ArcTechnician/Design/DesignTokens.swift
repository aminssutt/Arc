import SwiftUI
import UIKit

enum DesignTokens {
    enum Color {
        static let appBackground = dynamic(light: 0xeae8e2, dark: 0x070b11)
        static let header = dynamic(light: 0xf7f5ef, dark: 0x101a26)
        static let panel = dynamic(light: 0xfcfeff, dark: 0x1a2a3d)
        static let panelRaised = dynamic(light: 0xf1f5f9, dark: 0x0b111a)
        static let textPrimary = dynamic(light: 0x0b111a, dark: 0xf8fafc)
        static let textSecondary = dynamic(light: 0x475569, dark: 0xcbd5e1)
        static let textMuted = dynamic(light: 0x64748b, dark: 0x94a3b8)
        static let accent = dynamic(light: 0x0078ae, dark: 0x38d5ff)
        static let accentSubtle = dynamic(light: 0xe0f5fb, dark: 0x103b52)
        static let secondary = SwiftUI.Color(red: 0.1804, green: 0.9098, blue: 0.6941)
        static let warning = dynamic(light: 0xd98200, dark: 0xffc861)
        static let warningSubtle = dynamic(light: 0xffe2a8, dark: 0x4a310f)
        static let warningBorder = dynamic(light: 0xf59e0b, dark: 0xffad25)
        static let border = dynamic(light: 0xcbd5e1, dark: 0x334155)
        static let onPrimary = dynamic(light: 0xf8fafc, dark: 0x0b111a)
        static let activityDot = dynamic(light: 0x0788c5, dark: 0x38d5ff)

        private static func dynamic(light: UInt32, dark: UInt32) -> SwiftUI.Color {
            SwiftUI.Color(
                UIColor { traits in
                    UIColor(hex: traits.userInterfaceStyle == .dark ? dark : light)
                }
            )
        }
    }

    enum Typography {
        static let display = SwiftUI.Font.system(size: 64, weight: .bold)
        static let h1 = SwiftUI.Font.system(size: 48, weight: .bold)
        static let h2 = SwiftUI.Font.system(size: 40, weight: .bold)
        static let h3 = SwiftUI.Font.system(size: 32, weight: .semibold)
        static let h4 = SwiftUI.Font.system(size: 24, weight: .semibold)
        static let h5 = SwiftUI.Font.system(size: 20, weight: .semibold)
        static let h6 = SwiftUI.Font.system(size: 18, weight: .semibold)
        static let body = SwiftUI.Font.system(size: 16, weight: .regular)
        static let bodySmall = SwiftUI.Font.system(size: 14, weight: .regular)
        static let label = SwiftUI.Font.system(size: 13, weight: .medium)
        static let labelSmall = SwiftUI.Font.system(size: 12, weight: .medium)
        static let caption = SwiftUI.Font.system(size: 12, weight: .regular)

        // Button-specific type ramp (Figma "Section Button", node 38:6) — distinct from the H/Body scale above.
        static let buttonSmall = SwiftUI.Font.system(size: 14, weight: .semibold)
        static let buttonMedium = SwiftUI.Font.system(size: 16, weight: .semibold)
        static let buttonLarge = SwiftUI.Font.system(size: 18, weight: .semibold)
    }

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 24
    }

    enum Radius {
        static let sm: CGFloat = 6
        static let md: CGFloat = 8
        static let lg: CGFloat = 12
    }
}

private extension UIColor {
    convenience init(hex: UInt32) {
        self.init(
            red: CGFloat((hex >> 16) & 0xff) / 255,
            green: CGFloat((hex >> 8) & 0xff) / 255,
            blue: CGFloat(hex & 0xff) / 255,
            alpha: 1
        )
    }
}
