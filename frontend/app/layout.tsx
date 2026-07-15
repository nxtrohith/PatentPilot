import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PatentPilot — AI-Assisted Freedom-to-Operate Analysis",
  description:
    "PatentPilot is an AI-assisted Freedom-to-Operate workspace for patent analysis in drug discovery. Search relevant patents, perform AI analysis, and generate structured patentability reports.",
  keywords:
    "freedom to operate, FTO, patent analysis, drug discovery, AI patent analysis, SureChEMBL, patentability report",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,300&family=DM+Sans:wght@300;400;500;600&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
