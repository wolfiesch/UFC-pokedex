import React from "react";
import * as flags from "country-flag-icons/react/3x2";

interface CountryFlagProps {
  /** ISO 3166-1 alpha-2 country code (e.g., "US", "BR", "IE") */
  countryCode: string;
  /** Alt text for accessibility */
  alt?: string;
  /** CSS class name */
  className?: string;
  /** Flag width (default: 24px) */
  width?: number;
  /** Flag height (default: 16px) */
  height?: number;
}

/**
 * Renders a country flag SVG based on ISO 3166-1 alpha-2 country code.
 * Uses country-flag-icons library.
 */
export default function CountryFlag({
  countryCode,
  alt,
  className = "",
  width = 24,
  height = 16,
}: CountryFlagProps) {
  if (!countryCode || countryCode.length !== 2) {
    return null;
  }

  // Convert to uppercase (ISO codes are uppercase)
  const code = countryCode.toUpperCase() as keyof typeof flags;

  // Get flag component
  const FlagComponent = flags[code];

  if (!FlagComponent) {
    console.warn(`Flag not found for country code: ${code}`);
    return null;
  }

  return (
    <FlagComponent
      title={alt || code}
      className={className}
      style={{ width: `${width}px`, height: `${height}px` }}
    />
  );
}
