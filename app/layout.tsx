import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "我的股票篩選系統",
  description: "以 yfinance 資料與多頭排列邏輯打造的個人量化選股工具"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-Hant">
      <body>{children}</body>
    </html>
  );
}
