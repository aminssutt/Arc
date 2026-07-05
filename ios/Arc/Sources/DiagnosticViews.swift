import SwiftUI

// MARK: - Screen A — incoming diagnostic (dispatch ticket)

struct IncomingDiagnosticView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        if let d = model.diagnostic {
            ScrollView {
                VStack(spacing: 16) {
                    banner(d)
                    ticket(d)
                }
                .padding(.horizontal, 18)
                .padding(.top, 6)
                .padding(.bottom, 12)
            }
            .safeAreaInset(edge: .bottom) { actionBar }
        } else {
            AwaitingView()
        }
    }

    private func banner(_ d: Diagnostic) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "bolt.trianglebadge.exclamationmark.fill")
                .foregroundStyle(ArcTheme.blueText)
            Text("FIELD VALIDATION REQUESTED")
                .font(.system(.caption, design: .rounded).weight(.bold))
                .tracking(0.8)
                .foregroundStyle(ArcTheme.blueText)
            Spacer()
        }
    }

    private func ticket(_ d: Diagnostic) -> some View {
        ArcCard {
            VStack(alignment: .leading, spacing: 0) {
                // Header — location + severity
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 3) {
                        FieldLabel(text: "Location")
                        Text(d.site.id)
                            .font(.system(.title3, design: .rounded).weight(.bold))
                        Text(d.site.name)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        if let a = d.site.address, !a.isEmpty {
                            Text(a).font(.caption).foregroundStyle(.tertiary)
                        }
                    }
                    Spacer(minLength: 8)
                    if let f = d.primaryFailure { SeverityBadge(severity: f.severity) }
                }
                .padding(18)

                Divider()

                hero(d)

                Divider()

                // Probable cause — one sentence, no confidence
                VStack(alignment: .leading, spacing: 10) {
                    VStack(alignment: .leading, spacing: 6) {
                        FieldLabel(text: "Probable cause")
                        Text(d.probableCause).font(.headline)
                    }
                    if !d.secondaryFailures.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            FieldLabel(text: "Also detected")
                            ForEach(d.secondaryFailures) { f in
                                HStack(spacing: 8) {
                                    Circle()
                                        .fill(ArcTheme.severityColor(f.severity))
                                        .frame(width: 6, height: 6)
                                    Text("\(f.label) · \(f.equipment)")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(18)

                Divider()

                // Meta — incident id + received time
                HStack {
                    Label(d.incidentID, systemImage: "number")
                    Spacer()
                    Label(d.receivedAt.formatted(date: .omitted, time: .standard),
                          systemImage: "clock")
                }
                .font(.caption.monospaced())
                .foregroundStyle(.tertiary)
                .padding(18)
            }
        }
    }

    /// Hero block. With a telemetry `reading` -> value in XXL mono, alarm code as
    /// subtitle. Without it -> the alarm code is the hero (unchanged behaviour).
    @ViewBuilder private func hero(_ d: Diagnostic) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            FieldLabel(text: "Reading")
            if let r = d.reading {
                Text(r.display)
                    .font(.system(size: 40, weight: .bold, design: .monospaced))
                    .foregroundStyle(ArcTheme.blueText)
                    .minimumScaleFactor(0.5)
                    .lineLimit(1)
                Label(d.readingSubtitle, systemImage: "cpu")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                Text(d.heroValue)
                    .font(.system(size: 34, weight: .bold, design: .monospaced))
                    .foregroundStyle(ArcTheme.blueText)
                    .minimumScaleFactor(0.55)
                    .lineLimit(2)
                if let f = d.primaryFailure {
                    Label(f.equipment, systemImage: "cpu")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
    }

    private var actionBar: some View {
        HStack(spacing: 12) {
            Button(role: .destructive) {
                model.goToCounterMeasure()
            } label: {
                BigButtonLabel(title: "Refuse", systemImage: "xmark")
            }
            .buttonStyle(.bordered)
            .controlSize(.large)
            .tint(.red)

            Button {
                Task { await model.validate() }
            } label: {
                BigButtonLabel(title: "Validate", systemImage: "checkmark")
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .tint(ArcTheme.confirm)
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 12)
        .background(.bar)
    }
}

// MARK: - Screen B — counter-measurement on refuse

struct CounterMeasurementView: View {
    @Environment(AppModel.self) private var model
    @State private var valueText = ""
    @State private var unit = "V"
    @State private var validationError: String?
    @FocusState private var valueFocused: Bool

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Counter-measurement")
                        .font(.system(.title2, design: .rounded).weight(.bold))
                    Text("Enter what you measured on site. The agent re-diagnoses against it.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                ArcCard {
                    VStack(alignment: .leading, spacing: 14) {
                        HStack {
                            FieldLabel(text: "Measurement")
                            Spacer()
                            Text("DC voltage · busbar")
                                .font(.caption.monospaced())
                                .foregroundStyle(.tertiary)
                        }
                        HStack(alignment: .firstTextBaseline, spacing: 12) {
                            TextField("-53.9", text: $valueText)
                                .keyboardType(.numbersAndPunctuation)
                                .font(.system(size: 46, weight: .bold, design: .monospaced))
                                .foregroundStyle(valueText.isEmpty ? .secondary : ArcTheme.blueText)
                                .focused($valueFocused)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            TextField("V", text: $unit)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .font(.system(size: 26, weight: .semibold, design: .monospaced))
                                .foregroundStyle(.secondary)
                                .frame(width: 58)
                                .multilineTextAlignment(.center)
                        }
                    }
                    .padding(18)
                }

                if let validationError {
                    Label(validationError, systemImage: "exclamationmark.triangle.fill")
                        .font(.footnote)
                        .foregroundStyle(ArcTheme.warn)
                }
            }
            .padding(18)
        }
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: 8) {
                Button { submit() } label: {
                    BigButtonLabel(title: "Send", systemImage: "paperplane.fill")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .tint(ArcTheme.blue)

                Button("Back") { model.backToDiagnostic() }
                    .font(.subheadline)
                    .tint(.secondary)
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 12)
            .background(.bar)
        }
        .onAppear { valueFocused = true }
    }

    private func submit() {
        let normalized = valueText.trimmingCharacters(in: .whitespaces)
            .replacingOccurrences(of: ",", with: ".")
        guard let value = Double(normalized) else {
            validationError = "Enter a numeric value, e.g. -53.9"
            return
        }
        let unitValue = unit.trimmingCharacters(in: .whitespaces).isEmpty ? "V" : unit
        validationError = nil
        Task { await model.refuse(value: value, unit: unitValue) }
    }
}
