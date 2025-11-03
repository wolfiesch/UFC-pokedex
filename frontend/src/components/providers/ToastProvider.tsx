"use client";

import { Toaster } from "sonner";

/**
 * Toast provider component that wraps the app with Sonner toaster.
 * Provides toast notification functionality throughout the application.
 */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Toaster
        position="bottom-right"
        expand={false}
        richColors
        closeButton
        duration={5000}
        toastOptions={{
          classNames: {
            error: "border-destructive bg-destructive text-destructive-foreground",
            success: "border-green-500 bg-green-50 text-green-900",
            warning: "border-yellow-500 bg-yellow-50 text-yellow-900",
            info: "border-blue-500 bg-blue-50 text-blue-900",
          },
        }}
      />
    </>
  );
}
