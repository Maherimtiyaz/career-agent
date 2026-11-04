import type { Metadata } from "next";
import { QueryProvider } from "@/providers/QueryProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Career Agent | Your career, in motion",
    template: "%s | Career Agent",
  },
  description: "Find opportunities, manage applications, and make your next career move with clarity.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
