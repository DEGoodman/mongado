import type { Metadata, Viewport } from "next";
import { Space_Grotesk, Space_Mono } from "next/font/google";
import "@/styles/globals.scss";
import { siteConfig } from "@/lib/site-config";

// Load Space Grotesk font
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-space-grotesk",
  display: "swap",
});

// Load Space Mono font
const spaceMono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-space-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: siteConfig.metadata.title,
  description: siteConfig.metadata.description,
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
  openGraph: {
    title: siteConfig.metadata.title,
    description: siteConfig.metadata.description,
    siteName: siteConfig.name,
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary",
    title: siteConfig.metadata.title,
    description: siteConfig.metadata.description,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${spaceMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
