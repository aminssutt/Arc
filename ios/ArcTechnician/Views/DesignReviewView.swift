import SwiftUI

// Review surface for the Arc design-system components pulled from Figma
// ("01 Foundations" + Button/Badge/Card sections). Not part of the demo flow —
// reachable from RootView's toolbar for visual QA.
struct DesignReviewView: View {
    private let buttonVariants: [(String, ArcButtonVariant)] = [
        ("Primary", .primary),
        ("Secondary", .secondary),
        ("Ghost", .ghost),
        ("Warning", .warning),
        ("Warning Subtle", .warningSubtle),
    ]

    private let buttonSizes: [(String, ArcButtonSize)] = [
        ("Small", .small),
        ("Medium", .medium),
        ("Large", .large),
    ]

    private let badgeTones: [(String, ArcBadgeTone)] = [
        ("Primary", .primary),
        ("Secondary", .secondary),
        ("Warning", .warning),
        ("Neutral", .neutral),
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xl) {
                sectionHeader("Button", subtitle: "Style x Size x State — Figma node 38:6")
                buttonSection

                sectionHeader("Badge", subtitle: "Tone x Emphasis — Figma node 38:8")
                badgeSection

                sectionHeader("Card", subtitle: "Base surface — Figma node 38:9")
                cardSection
            }
            .padding(DesignTokens.Spacing.lg)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(DesignTokens.Color.appBackground.ignoresSafeArea())
        .navigationTitle("Design Review")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func sectionHeader(_ title: String, subtitle: String) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text(title)
                .font(DesignTokens.Typography.h4)
                .foregroundColor(DesignTokens.Color.textPrimary)
            Text(subtitle)
                .font(DesignTokens.Typography.caption)
                .foregroundColor(DesignTokens.Color.textSecondary)
        }
    }

    private var buttonSection: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
            ForEach(buttonVariants, id: \.0) { variantName, variant in
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    Text(variantName)
                        .font(DesignTokens.Typography.label)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                    HStack(spacing: DesignTokens.Spacing.md) {
                        ForEach(buttonSizes, id: \.0) { sizeName, size in
                            ArcButton(title: sizeName, variant: variant, size: size) {}
                        }
                        ArcButton(title: "Disabled", variant: variant, size: .small) {}
                            .disabled(true)
                    }
                }
            }
        }
    }

    private var badgeSection: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            ForEach(badgeTones, id: \.0) { toneName, tone in
                HStack(spacing: DesignTokens.Spacing.md) {
                    Text(toneName)
                        .font(DesignTokens.Typography.label)
                        .foregroundColor(DesignTokens.Color.textSecondary)
                        .frame(width: 90, alignment: .leading)
                    ArcBadge(label: "Active", tone: tone, emphasis: .solid)
                    ArcBadge(label: "Active", tone: tone, emphasis: .subtle)
                }
            }
        }
    }

    private var cardSection: some View {
        ArcCard(
            eyebrow: "Arc Card",
            title: "Investigation summary",
            footnote: "Variable-bound surface"
        ) {
            Text("A compact surface for timeline items, evidence snapshots, and agent status blocks.")
        }
        .frame(maxWidth: 360, alignment: .leading)
    }
}

#Preview {
    NavigationStack {
        DesignReviewView()
    }
}
