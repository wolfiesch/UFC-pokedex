import "./globals.css";
import type { Metadata } from "next";
import { ReactNode } from "react";

export const metadata: Metadata = {
  title: "UFC Fighter Pokedex",
  description: "Explore UFC fighters with a Pokedex-inspired interface.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-50">
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  );
}
