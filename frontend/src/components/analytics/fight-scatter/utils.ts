/**
 * Format an opponent's name using the legacy "F. Lastname" style.
 *
 * @param name - Raw opponent name from the API payload.
 * @returns Formatted name that fits comfortably above scatter markers.
 */
export function formatOpponentName(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0) {
    return "";
  }

  if (parts.length === 1) {
    return parts[0];
  }

  const [firstName, ...rest] = parts;
  const lastName = rest.join(" ");
  return `${firstName.charAt(0)}. ${lastName}`;
}
