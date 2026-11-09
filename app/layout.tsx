import type { Metadata } from "next";
import "./globals.css";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "BloodBridge AI - Smart Blood Donation Platform",
  description: "Autonomous Multi-Agent Blood Request Matching & Emergency Response Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={cn("h-full antialiased font-sans")}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
