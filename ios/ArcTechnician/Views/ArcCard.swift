import SwiftUI

// Arc base card — Figma "Section Card", node 38:9 / component 11:77.
struct ArcCard<Content: View>: View {
    var eyebrow: String?
    let title: String
    var footnote: String?
    @ViewBuilder var content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            if let eyebrow {
                Text(eyebrow.uppercased())
                    .font(DesignTokens.Typography.labelSmall)
                    .foregroundColor(DesignTokens.Color.accent)
            }
            Text(title)
                .font(DesignTokens.Typography.h6)
                .foregroundColor(DesignTokens.Color.textPrimary)
            content()
                .font(DesignTokens.Typography.bodySmall)
                .foregroundColor(DesignTokens.Color.textSecondary)
            if let footnote {
                Text(footnote)
                    .font(DesignTokens.Typography.caption)
                    .foregroundColor(DesignTokens.Color.textSecondary)
            }
        }
        .padding(20) // color/spacing-5 — not in DesignTokens.Spacing's 4/8/12/16/24 scale
        .background(DesignTokens.Color.panelRaised)
        .overlay(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.md)
                .stroke(DesignTokens.Color.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }
}

extension ArcCard where Content == EmptyView {
    init(eyebrow: String? = nil, title: String, footnote: String? = nil) {
        self.init(eyebrow: eyebrow, title: title, footnote: footnote) { EmptyView() }
    }
}
