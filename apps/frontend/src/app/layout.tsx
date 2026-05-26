import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OPERATOR",
  description: "AI-assisted gamified life-management command center."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="font-mono">{children}</body>
    </html>
  );
}
