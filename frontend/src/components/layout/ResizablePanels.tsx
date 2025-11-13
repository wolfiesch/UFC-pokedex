"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Width of the draggable separator between the sidebar and the main canvas.
 * A small handle keeps the affordance visible without occupying significant space.
 */
const HANDLE_WIDTH = 12;

/**
 * Type describing the data passed to sidebar render functions.
 */
export interface ResizableSidebarRenderContext {
  /** Callback allowing sidebar implementations to close themselves when rendered as an overlay. */
  closeSidebar: () => void;
  /** Indicates whether the sidebar is currently presented as an overlay (i.e. below the lg breakpoint). */
  isOverlay: boolean;
}

/**
 * Type describing the data passed to the content render function.
 */
export interface ResizableContentRenderContext {
  /** Current calculated width available to the primary content panel. */
  width: number;
  /** Height as reported by the internal ResizeObserver, enabling responsive charts. */
  height: number;
  /** Indicates whether the sidebar is currently acting as an overlay. */
  isOverlay: boolean;
}

/**
 * Props controlling the behaviour of the {@link ResizablePanels} component.
 */
export interface ResizablePanelsProps {
  /**
   * Render function for the sidebar. The function receives contextual helpers
   * describing whether the sidebar is overlayed and a callback to close it.
   */
  sidebar: (context: ResizableSidebarRenderContext) => ReactNode;
  /**
   * Render function for the main content area. It receives the calculated
   * width/height so visualisations can bind directly to layout changes.
   */
  content: (context: ResizableContentRenderContext) => ReactNode;
  /**
   * Minimum width the sidebar may shrink to when resized at the lg breakpoint and above.
   */
  minSidebarWidth?: number;
  /** Minimum width preserved for the primary content panel while resizing. */
  minContentWidth?: number;
  /**
   * Initial width used before persisted values load or when localStorage is unavailable.
   */
  initialSidebarWidth?: number;
  /**
   * Storage key used to persist the sidebar width between sessions. When omitted, persistence is disabled.
   */
  storageKey?: string;
  /** Optional class name applied to the root container. */
  className?: string;
  /** Optional class name forwarded to the sidebar wrapper. */
  sidebarClassName?: string;
  /** Optional class name applied to the content wrapper. */
  contentClassName?: string;
  /** Optional class name applied to the draggable handle. */
  handleClassName?: string;
  /**
   * Media query string representing the breakpoint at which the sidebar collapses into an overlay.
   * Defaults to Tailwind's lg breakpoint (min-width: 1024px).
   */
  collapseMediaQuery?: string;
  /**
   * Controlled flag toggling the sidebar visibility when collapsed. Consumers should manage this
   * to support explicit open/close buttons on smaller viewports.
   */
  isSidebarOpen?: boolean;
  /** Callback invoked when the collapsed sidebar should change visibility. */
  onSidebarOpenChange?: (open: boolean) => void;
  /** Optional id forwarded to the sidebar for accessibility (e.g. aria-controls). */
  sidebarId?: string;
}

/**
 * Two-panel layout with a resizable splitter and responsive overlay behaviour.
 *
 * The component exposes the calculated canvas width so that visualisations can
 * respond immediately to user-driven layout changes instead of relying on
 * layout thrashing or MutationObservers. Width persistence is handled via
 * localStorage, keeping the preferred proportions across navigations.
 */
export function ResizablePanels({
  sidebar,
  content,
  minSidebarWidth = 280,
  minContentWidth = 420,
  initialSidebarWidth = 360,
  storageKey = "fightweb:sidebar-width",
  className,
  sidebarClassName,
  contentClassName,
  handleClassName,
  collapseMediaQuery = "(min-width: 1024px)",
  isSidebarOpen = true,
  onSidebarOpenChange,
  sidebarId,
}: ResizablePanelsProps) {
  /** Root element reference used for pointer math and resize observers. */
  const containerRef = useRef<HTMLDivElement | null>(null);
  /** Reference capturing the content column to observe width/height changes. */
  const contentRef = useRef<HTMLDivElement | null>(null);
  /** Stores whether the user is actively dragging the separator. */
  const [isDragging, setIsDragging] = useState<boolean>(false);
  /**
   * Tracks whether the viewport is wide enough to display both panels side by side.
   * When false, the sidebar is rendered as an overlay.
   */
  const [isOverlayViewport, setIsOverlayViewport] = useState<boolean>(false);
  /**
   * Width value persisted across sessions. The value is clamped using container
   * dimensions before being applied to the layout.
   */
  const [sidebarWidth, setSidebarWidth] = useState<number>(initialSidebarWidth);
  /**
   * React state carrying the latest content width/height so callers can bind to them.
   */
  const [contentSize, setContentSize] = useState<{ width: number; height: number}>(
    () => ({ width: 0, height: 0 }),
  );

  /** Keep the latest sidebar width in a ref so we can persist it after drag ends. */
  const latestSidebarWidthRef = useRef<number>(initialSidebarWidth);

  /**
   * Persist the sidebar width to localStorage when the user stops dragging.
   */
  const persistWidth = useCallback((width: number) => {
    if (!storageKey) {
      return;
    }
    try {
      window.localStorage.setItem(storageKey, String(width));
    } catch (error) {
      // Access to localStorage can fail in privacy modes; swallow errors silently.
      console.warn("Unable to persist sidebar width", error);
    }
  }, [storageKey]);

  /** Helper closing the sidebar when in overlay mode. */
  const closeSidebar = useCallback(() => {
    onSidebarOpenChange?.(false);
  }, [onSidebarOpenChange]);

  /**
   * Clamp a sidebar width request using the current container dimensions.
   */
  const clampSidebarWidth = useCallback((desiredWidth: number) => {
    const container = containerRef.current;
    if (!container) {
      return desiredWidth;
    }
    const containerWidth = container.getBoundingClientRect().width;
    if (containerWidth <= 0) {
      return desiredWidth;
    }
    const maxSidebarWidth = Math.max(minSidebarWidth, containerWidth - minContentWidth);
    return Math.min(Math.max(desiredWidth, minSidebarWidth), maxSidebarWidth);
  }, [minContentWidth, minSidebarWidth]);

  /**
   * Update the shared content size whenever either the container or sidebar width changes.
   */
  const recalculateContentSize = useCallback((nextSidebarWidth: number) => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const containerWidth = container.getBoundingClientRect().width;
    const containerHeight = container.getBoundingClientRect().height;
    if (containerWidth <= 0) {
      return;
    }
    const usableWidth = isOverlayViewport
      ? containerWidth
      : Math.max(minContentWidth, containerWidth - nextSidebarWidth - HANDLE_WIDTH);
    setContentSize((current) => ({
      width: usableWidth,
      height: containerHeight > 0 ? containerHeight : current.height,
    }));
  }, [isOverlayViewport, minContentWidth]);

  /**
   * Load any persisted width from localStorage on mount.
   */
  useEffect(() => {
    if (!storageKey) {
      return;
    }
    try {
      const stored = window.localStorage.getItem(storageKey);
      if (!stored) {
        return;
      }
      const parsed = Number.parseFloat(stored);
      if (Number.isFinite(parsed)) {
        const clamped = clampSidebarWidth(parsed);
        setSidebarWidth(clamped);
        latestSidebarWidthRef.current = clamped;
        recalculateContentSize(clamped);
      }
    } catch (error) {
      console.warn("Unable to read persisted sidebar width", error);
    }
  }, [clampSidebarWidth, recalculateContentSize, storageKey]);

  /**
   * Watch the container for resize events (e.g. window resizes) to update
   * layout-dependent metrics.
   */
  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }
      const clamped = clampSidebarWidth(latestSidebarWidthRef.current);
      setSidebarWidth(clamped);
      recalculateContentSize(clamped);
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, [clampSidebarWidth, recalculateContentSize]);

  useEffect(() => {
    recalculateContentSize(latestSidebarWidthRef.current);
  }, [recalculateContentSize]);

  /**
   * Observe the content column to capture the current height for downstream consumers.
   */
  useEffect(() => {
    const element = contentRef.current;
    if (!element) {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }
      setContentSize((current) => ({
        width: current.width,
        height: entry.contentRect.height,
      }));
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);

  /**
   * Track viewport width to determine when the sidebar should behave like an overlay.
   */
  useEffect(() => {
    const mediaQuery = window.matchMedia(collapseMediaQuery);
    const updateOverlayState = (event: MediaQueryList | MediaQueryListEvent) => {
      const matches = "matches" in event ? event.matches : event.media === collapseMediaQuery;
      setIsOverlayViewport(!matches);
      if (matches) {
        onSidebarOpenChange?.(true);
      }
    };
    updateOverlayState(mediaQuery);
    mediaQuery.addEventListener("change", updateOverlayState);
    return () => {
      mediaQuery.removeEventListener("change", updateOverlayState);
    };
  }, [collapseMediaQuery, onSidebarOpenChange]);

  /**
   * Begin the dragging interaction when the separator is grabbed.
   */
  const handlePointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (isOverlayViewport) {
      return;
    }
    event.preventDefault();
    const handle = event.currentTarget;
    handle.setPointerCapture(event.pointerId);
    setIsDragging(true);
  }, [isOverlayViewport]);

  /**
   * Update widths while the user drags the handle.
   */
  const handlePointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging || isOverlayViewport) {
      return;
    }
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const rect = container.getBoundingClientRect();
    const pointerX = event.clientX - rect.left;
    const nextWidth = clampSidebarWidth(pointerX);
    latestSidebarWidthRef.current = nextWidth;
    setSidebarWidth(nextWidth);
    recalculateContentSize(nextWidth);
  }, [clampSidebarWidth, isDragging, isOverlayViewport, recalculateContentSize]);

  /**
   * Finish the dragging interaction and persist widths.
   */
  const handlePointerUp = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging || isOverlayViewport) {
      return;
    }
    event.currentTarget.releasePointerCapture(event.pointerId);
    setIsDragging(false);
    persistWidth(latestSidebarWidthRef.current);
  }, [isDragging, isOverlayViewport, persistWidth]);

  /**
   * Memoised data object shared with the sidebar render function.
   */
  const sidebarContext = useMemo<ResizableSidebarRenderContext>(() => ({
    closeSidebar,
    isOverlay: isOverlayViewport,
  }), [closeSidebar, isOverlayViewport]);

  /**
   * Memoised data object shared with the content render function.
   */
  const contentContext = useMemo<ResizableContentRenderContext>(() => ({
    width: contentSize.width,
    height: contentSize.height,
    isOverlay: isOverlayViewport,
  }), [contentSize.height, contentSize.width, isOverlayViewport]);

  const sidebarElement = sidebar(sidebarContext);
  const contentElement = content(contentContext);

  const overlayIsVisible = isOverlayViewport && isSidebarOpen;

  useEffect(() => {
    if (!overlayIsVisible) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeSidebar();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [closeSidebar, overlayIsVisible]);

  return (
    <>
      {overlayIsVisible ? (
        <div
          className="fightweb-sidebar-backdrop"
          onClick={closeSidebar}
          role="presentation"
        />
      ) : null}

      <div
        ref={containerRef}
        className={cn(
          "relative flex w-full gap-3",
          isDragging && "select-none",
          className,
        )}
      >
      <div
        id={sidebarId}
        className={cn(
          "fightweb-sidebar-base",
          sidebarClassName,
          isOverlayViewport
            ? cn(
                "fightweb-sidebar-overlay",
                isSidebarOpen
                  ? "fightweb-sidebar-visible"
                  : "fightweb-sidebar-hidden",
              )
            : "lg:flex",
        )}
        style={
          isOverlayViewport
            ? undefined
            : {
                width: sidebarWidth,
                flexBasis: sidebarWidth,
              }
        }
        aria-hidden={isOverlayViewport ? !isSidebarOpen : false}
      >
        {sidebarElement}
      </div>

      <div
        role="separator"
        aria-orientation="vertical"
        aria-hidden={isOverlayViewport}
        className={cn(
          "fightweb-resize-handle",
          handleClassName,
          isOverlayViewport && "hidden",
        )}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      />

        <div
          ref={contentRef}
          className={cn("flex min-h-full flex-1 flex-col", contentClassName)}
        >
          {contentElement}
        </div>
      </div>
    </>
  );
}
