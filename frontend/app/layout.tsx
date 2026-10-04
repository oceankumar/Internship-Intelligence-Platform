import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Internship Intelligence",
  description: "Discovery dashboard for paid, profile-aligned internships",
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
