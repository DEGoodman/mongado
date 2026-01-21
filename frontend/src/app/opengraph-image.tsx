import { ImageResponse } from "next/og";
import { siteConfig } from "@/lib/site-config";

export const runtime = "edge";

export const alt = siteConfig.metadata.title;
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #FAFAF8 0%, #F4F6F9 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        {/* Logo - Brutalist M with drop shadow */}
        <div
          style={{
            position: "relative",
            width: 140,
            height: 140,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 40,
          }}
        >
          {/* Orange drop shadow */}
          <span
            style={{
              position: "absolute",
              fontSize: 120,
              fontWeight: 900,
              color: "#D96D32",
              left: 8,
              top: 8,
            }}
          >
            M
          </span>
          {/* Black M */}
          <span
            style={{
              position: "absolute",
              fontSize: 120,
              fontWeight: 900,
              color: "#111827",
              left: 0,
              top: 0,
            }}
          >
            M
          </span>
        </div>

        {/* Site name */}
        <div
          style={{
            fontSize: 64,
            fontWeight: 700,
            color: "#1F2937",
            marginBottom: 16,
          }}
        >
          {siteConfig.name}
        </div>

        {/* Author */}
        <div
          style={{
            fontSize: 32,
            color: "#4B5563",
            marginBottom: 8,
          }}
        >
          {siteConfig.author.name}
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 24,
            color: "#6B7280",
          }}
        >
          {siteConfig.author.title}
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}
