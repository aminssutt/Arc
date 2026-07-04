import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
