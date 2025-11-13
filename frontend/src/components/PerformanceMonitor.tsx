"use client";

import { useEffect } from "react";
import { initPerformanceMonitoring } from "@/lib/utils/performance-monitor";

/**
 * Client component to initialize performance monitoring
 * Must be a separate client component since RootLayout is a server component
 */
export function PerformanceMonitor() {
  useEffect(() => {
    // Initialize performance monitoring on mount
    initPerformanceMonitoring();
  }, []);

  return null; // This component doesn't render anything
}
