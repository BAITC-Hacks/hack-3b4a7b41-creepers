import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Электрокомплект | AI-консультант",
  description: "AI-консультант по электротехнической продукции",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="ru"><body>{children}</body></html>;
}
