import { clsx, type ClassValue } from "clsx";

/**
 * Utility for composing conditional Tailwind class strings.
 * Mirrors the helper shipped with the ShadCN UI starter.
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}
