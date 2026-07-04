import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Arc — NOC Control Room",
  description: "Live reasoning cockpit for telecom fault response — grounded, cited, human-in-the-loop.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
