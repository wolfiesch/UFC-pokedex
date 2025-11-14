import { describe, expect, it } from "vitest";

import {
  DEFAULT_CLIENT_API_BASE_URL,
  resolveServerApiBaseUrl,
} from "../api-base-url";

describe("resolveServerApiBaseUrl", () => {
  it("prefers the rewrite URL when provided", () => {
    const result = resolveServerApiBaseUrl({
      rewriteUrl: "https://api.example.com",
      publicUrl: "https://public.example.com",
      ssrUrl: "https://ssr.example.com",
    });

    expect(result).toBe("https://api.example.com");
  });

  it("falls back to the public URL when rewrite is absent", () => {
    const result = resolveServerApiBaseUrl({
      rewriteUrl: "  \t  ",
      publicUrl: "https://public.example.com/base",
      ssrUrl: null,
    });

    expect(result).toBe("https://public.example.com/base");
  });

  it("uses the SSR URL when only that value is configured", () => {
    const result = resolveServerApiBaseUrl({
      publicUrl: undefined,
      rewriteUrl: undefined,
      ssrUrl: "https://ssr.example.com",
    });

    expect(result).toBe("https://ssr.example.com");
  });

  it("returns the default fallback when no configuration is present", () => {
    const result = resolveServerApiBaseUrl({});

    expect(result).toBe(DEFAULT_CLIENT_API_BASE_URL);
  });
});
