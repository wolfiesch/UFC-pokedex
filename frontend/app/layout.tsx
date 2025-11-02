import "./globals.css";
import Link from "next/link";
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
        <div className="flex min-h-screen flex-col">
          <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur">
            <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4">
              <Link
                href="/"
                aria-label="Navigate to the UFC Fighter Pokedex home"
                className="text-lg font-semibold text-pokedexYellow transition hover:text-yellow-300"
              >
                UFC Fighter Pokedex
              </Link>
              <nav aria-label="Primary navigation" className="flex items-center gap-4 text-sm">
                <Link
                  href="/"
                  className="rounded-md px-3 py-2 text-slate-300 transition hover:bg-slate-900 hover:text-slate-100"
                >
                  Home
                </Link>
                <Link
                  href="/stats"
                  className="rounded-md px-3 py-2 text-slate-300 transition hover:bg-slate-900 hover:text-slate-100"
                >
                  Stats Hub
                </Link>
              </nav>
            </div>
          </header>
          <main className="flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
