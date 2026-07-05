import type { Metadata } from "next";
import { Saira, Saira_Condensed, JetBrains_Mono } from "next/font/google";
import { LenisProvider } from "@/motion/LenisProvider";
import "./globals.css";

// Industrial / telecom type system. Saira powers display + body (its
// variable also aliases --font-sans in globals.css); Saira Condensed = stats;
// JetBrains Mono = labels / data. Variables are wired onto <html> below.
const saira = Saira({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-display",
  display: "swap",
});

const sairaCondensed = Saira_Condensed({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-condensed",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Arc Control Room",
  description: "NOC control-room web for Arc incident validation demos",
};

// Runs before hydration to avoid a light/dark flash: localStorage override
// wins, otherwise follow the OS preference. Kept inline (no external script)
// so it executes synchronously in <head>.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem('arc-theme');
    var theme = stored === 'light' || stored === 'dark'
      ? stored
      : (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.documentElement.style.colorScheme = theme;
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning: the theme init script sets class/style on
    // <html> before hydration by design.
    <html
      lang="en"
      suppressHydrationWarning
      className={`${saira.variable} ${sairaCondensed.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>
        <LenisProvider>{children}</LenisProvider>
      </body>
    </html>
  );
}
