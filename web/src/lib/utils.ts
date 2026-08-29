import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTimeIST(date: Date = new Date()): string {
  return date.toLocaleTimeString("en-IN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatMinutes(mins: number): string {
  if (mins === 0) return "ON TIME";
  if (mins > 0) return `+${mins}M`;
  return `${mins}M`;
}
