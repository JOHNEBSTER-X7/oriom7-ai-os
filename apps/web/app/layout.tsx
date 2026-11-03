import type { Metadata } from "next";
import AccessibilityProvider from "../components/AccessibilityProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORIOM7 — Accessible AI Search",
  description: "ORIOM7 universal search and intelligence with adaptive accessibility.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AccessibilityProvider>{children}</AccessibilityProvider>
      </body>
    </html>
  );
}
