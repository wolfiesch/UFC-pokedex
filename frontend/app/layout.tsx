import "./globals.css";
import type { Metadata } from "next";
import { ReactNode } from "react";

import { SiteHeader } from "@/components/layout/site-header";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ToastProvider } from "@/components/providers/ToastProvider";
import { CommandPaletteProvider } from "@/components/providers/CommandPaletteProvider";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ThemeProvider } from "@/components/providers/ThemeProvider";

export const metadata: Metadata = {
  title: "UFC Fighter Pokedex",
  description: "Explore UFC fighters with a Pokedex-inspired interface.",
  icons: {
    icon: [
      {
        url: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🥊</text></svg>",
        type: "image/svg+xml",
      },
    ],
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
(function() {
  try {
    var theme = localStorage.getItem('ufc-pokedex-theme');
    if (!theme) {
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.classList.add(theme);
  } catch (e) {}
})();
            `,
          }}
        />
      </head>
      <body>
        <ErrorBoundary>
          <QueryProvider>
            <ToastProvider>
              <CommandPaletteProvider>
                <ThemeProvider>
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
                </ThemeProvider>
              </CommandPaletteProvider>
            </ToastProvider>
          </QueryProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
