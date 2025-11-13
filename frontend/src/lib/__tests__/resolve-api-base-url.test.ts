import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "../resolve-api-base-url";

describe("resolveApiBaseUrl", () => {
  it("normalizes scheme-less localhost values to http", () => {
    // Explicitly verify that the helper adds an http scheme for local targets so that
    // downstream fetch logic always receives an absolute URL.
    const result: string = resolveApiBaseUrl(
      "localhost:8000",
      "http://fallback.test",
    );
    expect(result).toBe("http://localhost:8000");
  });

  it("returns normalized fallback when raw value is empty", () => {
    // The fallback should be normalized by trimming the trailing slash, matching the
    // behaviour used when parsing environment configuration.
    const result: string = resolveApiBaseUrl("   ", "http://example.com/api/");
    expect(result).toBe("http://example.com/api");
  });

  it("preserves https scheme when already provided", () => {
    // Non-local values with a full scheme should be respected and normalized without
    // forcing an http downgrade.
    const result: string = resolveApiBaseUrl(
      "https://api.example.com/v1/",
      "http://fallback.test",
    );
    expect(result).toBe("https://api.example.com/v1");
  });
});
