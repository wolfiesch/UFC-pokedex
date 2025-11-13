"use client";

import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

/**
 * Describes the only theme variants supported by the application.
 * The union keeps the type-system explicit which in turn avoids
 * accidentally setting unsupported values on the HTML root element.
 */
export type ThemeVariant = "dark" | "light";

/**
 * The localStorage key under which the theme preference is persisted.
 * Keeping the key centralized avoids accidental typos across hooks
 * and effect handlers that interact with the persistence layer.
 */
const THEME_STORAGE_KEY = "ufc-pokedex-theme";

/**
 * Interface describing the context value. Explicitly annotating each
 * property helps downstream consumers understand the API at a glance
 * and allows the compiler to surface incorrect usage immediately.
 */
export interface ThemeContextValue {
  /** The currently active theme variant. */
  readonly theme: ThemeVariant;
  /**
   * Mutator that allows consumers to directly set the theme variant.
   * This is useful when building future controls such as dropdown selectors.
   */
  readonly setTheme: (nextTheme: ThemeVariant) => void;
  /**
   * Convenience function that flips between the only two supported theme
   * values. The toggle is used by the header control added in this change.
   */
  readonly toggleTheme: () => void;
}

/**
 * Internal React context used to share the theme state across the app.
 * The initial value is deliberately undefined to allow the custom hook to
 * throw meaningful errors when the provider is missing.
 */
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

/**
 * Applies the provided theme value to the root `<html>` element so that
 * Tailwind's `dark` class strategy can drive the design tokens defined in
 * `globals.css`. Extracted into a stable callback to avoid recreating the
 * function on every render and to keep all DOM mutations in one place.
 */
const applyThemeToDocument = (nextTheme: ThemeVariant): void => {
  if (typeof document === "undefined") {
    return;
  }

  const rootElement = document.documentElement;
  rootElement.classList.remove("dark", "light");
  rootElement.classList.add(nextTheme);
  rootElement.dataset.theme = nextTheme;
};

/**
 * Provider component that encapsulates the theme state machine. The provider
 * ensures dark mode is the default while still respecting a previously stored
 * preference when available. Any component rendered beneath it can read the
 * current theme or toggle it via the exposed context value.
 */
export function ThemeProvider({
  children,
}: {
  readonly children: ReactNode;
}): JSX.Element {
  const [theme, setThemeState] = useState<ThemeVariant>("dark");

  useEffect(() => {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === "dark" || storedTheme === "light") {
      setThemeState(storedTheme);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    applyThemeToDocument(theme);
  }, [theme]);

  const setTheme = useCallback((nextTheme: ThemeVariant) => {
    setThemeState(nextTheme);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((previousTheme) =>
      previousTheme === "dark" ? "light" : "dark",
    );
  }, []);

  const contextValue = useMemo<ThemeContextValue>(
    () => ({
      theme,
      setTheme,
      toggleTheme,
    }),
    [theme, setTheme, toggleTheme],
  );

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Convenience hook that wraps `useContext` so components can easily access the
 * theme API. The explicit error helps developers catch configuration issues in
 * development instead of failing silently with an undefined context value.
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider instance");
  }

  return context;
}
