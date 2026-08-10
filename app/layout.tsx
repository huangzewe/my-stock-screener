import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "台股成長科技選股工作台",
  description: "以臺灣證交所與櫃買中心資料，評估價值、品質成長、動能與資料完整度的台股全市場量化篩選工具"
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
