"use client";

import { useEffect, useState } from "react";

import type { ColorVisionMode } from "@/constants/divisionColors";

/**
 * Observe accessibility-related media queries (forced colours and high
 * contrast) along with a manual `data-color-vision` override on the document
 * element.  The hook returns the preferred colour vision mode so components can
 * choose between standard and colourblind-friendly palettes.
 */
export function useColorVisionMode(): ColorVisionMode {
  const [mode, setMode] = useState<ColorVisionMode>("standard");

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const root = window.document.documentElement;
    const queries = [
      window.matchMedia("(forced-colors: active)"),
      window.matchMedia("(prefers-contrast: more)"),
    ];

    const evaluatePreference = () => {
      const override = root.getAttribute("data-color-vision");
      if (override === "colorblind") {
        setMode("colorblind");
        return;
      }
      if (override === "standard") {
        setMode("standard");
        return;
      }

      const prefersAccessiblePalette = queries.some((query) => query.matches);
      setMode(prefersAccessiblePalette ? "colorblind" : "standard");
    };

    evaluatePreference();

    const unsubscribe = queries.map((query) => {
      const handler = () => evaluatePreference();
      if ("addEventListener" in query) {
        query.addEventListener("change", handler);
        return () => query.removeEventListener("change", handler);
      }
      query.addListener(handler);
      return () => query.removeListener(handler);
    });

    const observer = new MutationObserver(() => evaluatePreference());
    observer.observe(root, { attributes: true, attributeFilter: ["data-color-vision"] });

    return () => {
      observer.disconnect();
      unsubscribe.forEach((cleanup) => cleanup());
    };
  }, []);

  return mode;
}

