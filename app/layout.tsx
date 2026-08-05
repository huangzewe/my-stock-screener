import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "我的股票篩選系統",
  description: "個人股票篩選、觀察清單與指標比較工具"
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
