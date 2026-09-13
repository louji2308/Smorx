import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smorx — System Health",
  description: "Software Evolution Intelligence System — Phase 0 health path",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="body">{children}</body>
    </html>
  );
}