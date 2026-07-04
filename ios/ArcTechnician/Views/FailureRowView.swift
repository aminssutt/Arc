import SwiftUI

struct FailureRowView: View {
    let failure: DetectedFailure

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack(alignment: .top, spacing: DesignTokens.Spacing.md) {
                Circle()
                    .fill(DesignTokens.Color.warning)
                    .frame(width: 10, height: 10)
                    .padding(.top, 5)

                VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                    Text(failure.code)
                        .font(.body.weight(.semibold))
                        .foregroundStyle(DesignTokens.Color.textPrimary)

                    Text(failure.equipment)
                        .font(.callout)
                        .foregroundStyle(DesignTokens.Color.textSecondary)

                    Text(failure.severity.rawValue)
                        .font(.footnote.monospaced())
                        .foregroundStyle(DesignTokens.Color.accent)
                }
            }
        }
        .padding(DesignTokens.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(DesignTokens.Color.panelRaised)
        .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.md))
    }
}

#Preview {
    FailureRowView(
        failure: DetectedFailure(
            id: "F2",
            code: "DC_UNDERVOLTAGE",
            severity: .major,
            equipment: "busbar"
        )
    )
    .padding()
    .background(DesignTokens.Color.appBackground)
}
