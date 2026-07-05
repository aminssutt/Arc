import SwiftUI

struct RootView: View {
    @Environment(AppModel.self) private var model
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            ZStack {
                ArcTheme.bg.ignoresSafeArea()
                switch model.route {
                case .awaiting:       AwaitingView()
                case .diagnostic:     IncomingDiagnosticView()
                case .counterMeasure: CounterMeasurementView()
                case .confirmation:   ConfirmationView()
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) { ArcWordmark() }
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showSettings = true } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("Settings")
                }
            }
            .toolbarBackground(.hidden, for: .navigationBar)
            .sheet(isPresented: $showSettings) { SettingsView() }
        }
        .tint(ArcTheme.blueText)
    }
}

// MARK: - Awaiting (fallback + foreground-push landing)

struct AwaitingView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(spacing: 22) {
            Spacer()
            ZStack {
                Circle()
                    .fill(ArcTheme.blue.opacity(0.12))
                    .frame(width: 132, height: 132)
                Circle()
                    .strokeBorder(ArcTheme.blue.opacity(0.30), lineWidth: 1)
                    .frame(width: 132, height: 132)
                Image(systemName: "antenna.radiowaves.left.and.right")
                    .font(.system(size: 46, weight: .regular))
                    .foregroundStyle(ArcTheme.blueText)
                    .symbolEffect(.variableColor.iterative, options: .repeating)
            }
            VStack(spacing: 6) {
                Text("Awaiting dispatch")
                    .font(.system(.title2, design: .rounded).weight(.semibold))
                Text(model.pushStatus)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            Spacer()
            Button { model.loadSampleIncident() } label: {
                Text("Load sample incident")
                    .font(.subheadline.weight(.medium))
                    .frame(maxWidth: .infinity, minHeight: 24)
                    .padding(.vertical, 4)
            }
            .buttonStyle(.bordered)
            .controlSize(.large)
            .tint(ArcTheme.blueText)
            Text("You'll be notified the instant a fault is matched to you.")
                .font(.caption2)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
        }
        .padding(.horizontal, 28)
        .padding(.bottom, 24)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Settings

struct SettingsView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        @Bindable var model = model
        NavigationStack {
            Form {
                Section("Backend") {
                    TextField("http://192.168.1.10:8000", text: $model.baseURL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                        .font(.body.monospaced())
                    Text("Use the Mac's LAN IP and port 8000 — never localhost.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Device") {
                    LabeledContent("APNs token") {
                        Text(model.deviceTokenHex.map { String($0.prefix(16)) + "…" } ?? "not registered")
                            .font(.footnote.monospaced())
                            .foregroundStyle(.secondary)
                    }
                    LabeledContent("Status") {
                        Text(model.pushStatus)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.trailing)
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .presentationDetents([.medium, .large])
        .preferredColorScheme(.dark)
    }
}
