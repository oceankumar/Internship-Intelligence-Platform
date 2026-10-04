import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InternAI | Internship Intelligence Platform",
  description: "Discover, evaluate, and track internships with explainable ranking, eligibility analysis and listing-risk intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
