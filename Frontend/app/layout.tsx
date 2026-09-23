import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EKT Copilot — закупки без лишних поисков",
  description:
    "Наличие, характеристики, аналоги и подготовка закупки в одном окне. Creepers · HackAlem AI 2026.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
