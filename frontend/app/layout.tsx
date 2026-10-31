import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Saarthi AI — Government Scheme Navigator",
    template: "%s | Saarthi AI",
  },
  description:
    "Saarthi AI is an open-source, multilingual digital caseworker that matches Indian citizens to government welfare schemes, checks eligibility, and prepares application checklists.",
  applicationName: "Saarthi AI",
  keywords: [
    "government schemes",
    "welfare",
    "eligibility",
    "Gemma",
    "open source",
    "India",
  ],
  authors: [{ name: "Saarthi AI contributors" }],
  openGraph: {
    title: "Saarthi AI — Government Scheme Navigator",
    description:
      "Find welfare schemes, understand eligibility, and prepare applications with a privacy-conscious AI caseworker.",
    type: "website",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
