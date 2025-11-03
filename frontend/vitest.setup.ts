import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

class MockResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

const globalWithResizeObserver = globalThis as typeof globalThis & {
  ResizeObserver?: unknown;
};

if (typeof globalWithResizeObserver.ResizeObserver === "undefined") {
  globalWithResizeObserver.ResizeObserver = MockResizeObserver;
}
