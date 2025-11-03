import "./globals.css";
import type { Metadata } from "next";
import { ReactNode } from "react";

import { SiteHeader } from "@/components/layout/site-header";

export const metadata: Metadata = {
  title: "UFC Fighter Pokedex",
  description: "Explore UFC fighters with a Pokedex-inspired interface.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen flex-col bg-background text-foreground">
          <SiteHeader />
          <main className="flex-1 pb-16">{children}</main>
          <footer className="border-t border-border/80 py-6">
            <div className="container flex flex-col gap-2 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
              <p>© {new Date().getFullYear()} UFC Fighter Pokedex</p>
              <p className="text-xs uppercase tracking-[0.3em]">
                Built for fight data enthusiasts
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
