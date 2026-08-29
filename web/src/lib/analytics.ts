/**
 * Umami Analytics Integration (Open Source, Cookieless)
 *
 * Rules:
 * 1. Disabled by default.
 * 2. Only active when both VITE_UMAMI_SRC and VITE_UMAMI_ID env vars are set.
 * 3. Requires explicit cookie consent in localStorage["rtx-consent"] === "accepted".
 * 4. Zero PII ever tracked.
 */

export const CONSENT_KEY = "rtx-consent";

export type ConsentStatus = "accepted" | "declined" | "pending";

export function getConsentStatus(): ConsentStatus {
  if (typeof window === "undefined") return "pending";
  const stored = localStorage.getItem(CONSENT_KEY);
  if (stored === "accepted" || stored === "declined") {
    return stored;
  }
  return "pending";
}

export function setConsentStatus(status: "accepted" | "declined"): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CONSENT_KEY, status);
  if (status === "accepted") {
    initAnalytics();
  } else {
    removeAnalyticsScript();
  }
}

export function isAnalyticsActive(): boolean {
  if (typeof window === "undefined") return false;
  const scriptSrc = import.meta.env.VITE_UMAMI_SRC;
  const websiteId = import.meta.env.VITE_UMAMI_ID;
  const hasConsent = getConsentStatus() === "accepted";
  return Boolean(scriptSrc && websiteId && hasConsent);
}

export function initAnalytics(): void {
  if (typeof window === "undefined") return;
  const scriptSrc = import.meta.env.VITE_UMAMI_SRC;
  const websiteId = import.meta.env.VITE_UMAMI_ID;

  if (!scriptSrc || !websiteId || getConsentStatus() !== "accepted") {
    return;
  }

  // Avoid injecting twice
  if (document.getElementById("umami-script")) {
    return;
  }

  const script = document.createElement("script");
  script.id = "umami-script";
  script.async = true;
  script.defer = true;
  script.src = scriptSrc;
  script.setAttribute("data-website-id", websiteId);
  document.head.appendChild(script);
}

function removeAnalyticsScript(): void {
  if (typeof window === "undefined") return;
  const script = document.getElementById("umami-script");
  if (script && script.parentNode) {
    script.parentNode.removeChild(script);
  }
}

export function trackEvent(eventName: string, eventData?: Record<string, string | number | boolean>): void {
  if (typeof window === "undefined" || !isAnalyticsActive()) return;

  const umami = (window as unknown as { umami?: { track: (name: string, data?: Record<string, string | number | boolean>) => void } }).umami;
  if (umami && typeof umami.track === "function") {
    umami.track(eventName, eventData);
  }
}
