import type { Config } from "tailwindcss";

function themeColor(name: string) {
  return `rgb(var(--color-${name}) / <alpha-value>)`;
}

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        // Industrial / telecom-engineering type system (ported from ECU).
        // Saira drives display + body; Saira Condensed = spec-sheet numerals;
        // JetBrains Mono = labels / data / coordinates. CSS vars are injected
        // by next/font in layout.tsx (--font-display/--font-sans/--font-condensed/
        // --font-mono); --font-sans aliases --font-display in globals.css.
        display: ["var(--font-display)", '"Saira"', '"Saira Condensed"', "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", '"Saira"', "system-ui", "sans-serif"],
        condensed: ["var(--font-condensed)", '"Saira Condensed"', '"Saira"', "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", '"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        // ── Arc semantic tokens (theme-aware) ────────────────────────────
        // Values live as CSS variables in globals.css (:root = light,
        // .dark = dark) and are now remapped onto the warm + tricolore
        // palette. Every daniwavy token name below still resolves — pages
        // and components that reference them keep working, they just render
        // in the new palette. ThemeToggle flips these via the .dark class.
        background: themeColor("background"),
        panel: themeColor("panel"),
        raised: themeColor("raised"),
        border: themeColor("border"),
        muted: themeColor("muted"),
        text: themeColor("text"),
        accent: themeColor("accent"),
        accentSubtle: themeColor("accent-subtle"),
        secondary: themeColor("secondary"),
        warning: themeColor("warning"),
        outer: themeColor("outer"),
        header: themeColor("header"),
        panelMuted: themeColor("panel-muted"),
        borderSubtle: themeColor("border-subtle"),
        borderStrong: themeColor("border-strong"),
        textSecondary: themeColor("text-secondary"),
        accentBright: themeColor("accent-bright"),
        warningBright: themeColor("warning-bright"),
        warningDeep: themeColor("warning-deep"),

        // ── ECU neutral paper / ink scale (warm, static) ─────────────────
        // The editorial light surfaces used by ported ECU section classes.
        paper: "#FAFAF7",
        "paper-raised": "#FFFFFF",
        ink: {
          DEFAULT: "#131311",
          soft: "#4C4B45",
          faint: "#8A897F",
          line: "#E6E5DD",
        },
        // ── Dark surfaces (hero, live panels) — warm near-black base ──────
        surface: {
          DEFAULT: "#0b0b0f",
          raised: "#161318",
          line: "#2A2730",
        },

        // ── Tricolore brand accents (static; readable on paper + surface) ─
        // ember = detection / fault / primary CTA — de-oranged to the brand blue
        // (global app blue). Key name kept so existing `*-ember` classes resolve.
        ember: {
          DEFAULT: "#0078AE",
          dim: "#3ea0cf",
          deep: "#005f8a", // readable on paper
        },
        // arc = reasoning / agents
        arc: {
          DEFAULT: "#4d9dff",
          dim: "#8fbfff",
          deep: "#1f6fd6", // readable on paper
        },
        // resolve = validated / resolved
        resolve: {
          DEFAULT: "#3ecf8e",
          dim: "#86e0b8",
          deep: "#1f9c68", // readable on paper
        },
        // danger = pivot / refusal. DEFAULT stays theme-aware (CSS var) so the
        // pre-existing `bg-danger`/`text-danger` usages flip with the theme;
        // dim/deep are static tricolore steps for ported ECU-style classes.
        danger: {
          DEFAULT: themeColor("danger"),
          dim: "#f0888c",
          deep: "#b02b30",
        },
        // warn = logistics / human-loop — de-ambered to a distinct blue-cyan so
        // nothing reads orange, while staying separable from ember/arc.
        warn: {
          DEFAULT: "#0ea5e9",
          dim: "#7dd3fc",
          deep: "#0369a1",
        },
        // signal = alias → resolve, so any ported ECU `*-signal` class resolves.
        signal: {
          DEFAULT: "#3ecf8e",
          dim: "#86e0b8",
          deep: "#1f9c68",
        },
      },
      boxShadow: {
        glow: "0 0 16px 0 rgb(var(--color-accent) / 0.28)",
        glowWarning: "0 0 16px 0 rgb(var(--color-warning) / 0.25)",
        glowEmber: "0 0 28px -6px rgb(0 120 174 / 0.6)",
        glowResolve: "0 0 28px -8px rgb(62 207 142 / 0.5)",
      },
      fontSize: {
        // Industrial-grotesque display scale — tuned for Saira (tight tracking,
        // compact leading so headings read engineered, not editorial).
        display: ["clamp(2.6rem, 5.6vw, 4.4rem)", { lineHeight: "0.98", letterSpacing: "-0.022em" }],
        "display-sm": ["clamp(1.9rem, 3.6vw, 3rem)", { lineHeight: "1.02", letterSpacing: "-0.018em" }],
        // Arc numeric type ramp (preserved — pages reference these).
        h1: ["48px", { lineHeight: "58px" }],
        h2: ["40px", { lineHeight: "48px" }],
        h3: ["32px", { lineHeight: "40px" }],
        h4: ["24px", { lineHeight: "32px" }],
        h5: ["20px", { lineHeight: "28px" }],
        h6: ["18px", { lineHeight: "26px" }],
        body: ["16px", { lineHeight: "24px" }],
        "body-sm": ["14px", { lineHeight: "20px" }],
        label: ["13px", { lineHeight: "18px" }],
        "label-sm": ["12px", { lineHeight: "16px" }],
        caption: ["12px", { lineHeight: "16px" }],
      },
      letterSpacing: {
        label: "0.24em",
        tight: "-0.022em",
      },
      maxWidth: {
        prose: "42rem",
        narrative: "56rem",
        content: "84rem",
        wide: "92rem",
      },
      borderRadius: {
        card: "14px",
      },
      transitionTimingFunction: {
        expo: "cubic-bezier(0.16, 1, 0.3, 1)",
        // crisp, controlled — the mechanic motion signature (fast-in, firm settle).
        mech: "cubic-bezier(0.22, 0.61, 0.18, 1)",
      },
      keyframes: {
        "wheel-spin": {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        "signal-pulse": {
          "0%, 100%": { opacity: "0.35" },
          "50%": { opacity: "1" },
        },
        "dash-flow": {
          to: { strokeDashoffset: "-24" },
        },
      },
      animation: {
        "wheel-spin": "wheel-spin 0.8s linear infinite",
        "signal-pulse": "signal-pulse 1.8s ease-in-out infinite",
        "dash-flow": "dash-flow 1s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
