import type { Config } from "tailwindcss";

function themeColor(name: string) {
  return `rgb(var(--color-${name}) / <alpha-value>)`;
}

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Arc design system semantic colors — values live as CSS variables in
        // globals.css (:root = light, .dark = dark) so every utility class
        // here just resolves through the current theme. See tokens listed
        // there for the Figma node references (70:108, 84:83/84:867).
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
        danger: themeColor("danger"),
        outer: themeColor("outer"),
        header: themeColor("header"),
        panelMuted: themeColor("panel-muted"),
        borderSubtle: themeColor("border-subtle"),
        borderStrong: themeColor("border-strong"),
        textSecondary: themeColor("text-secondary"),
        accentBright: themeColor("accent-bright"),
        warningBright: themeColor("warning-bright"),
        warningDeep: themeColor("warning-deep")
      },
      boxShadow: {
        // Arc/효과 Effect/글로우 Glow/프라이머리 Primary
        glow: "0 0 16px 0 rgb(var(--color-accent) / 0.28)",
        glowWarning: "0 0 16px 0 rgb(var(--color-warning) / 0.25)"
      },
      fontSize: {
        // Arc type ramp (Figma "01 Foundations" > Typography, node 18:2)
        display: ["64px", { lineHeight: "72px" }],
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
        caption: ["12px", { lineHeight: "16px" }]
      }
    }
  },
  plugins: [],
};

export default config;
