import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Skycast · Forecast skill explorer",
  description:
    "Gradient-boosted 1–7 day weather forecasts trained on 25 years of history for any city, backtested against persistence, climatology and numerical weather prediction.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
