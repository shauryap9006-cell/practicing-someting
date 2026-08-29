import React from "react";
import { Helmet } from "react-helmet-async";
import { SITE } from "@/config/site";

export function getSiteUrl(): string {
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin;
  }
  const envUrl = import.meta.env.VITE_SITE_URL;
  if (envUrl && typeof envUrl === "string") {
    return envUrl.replace(/\/$/, "");
  }
  return "https://railtwin-x.local";
}

interface SEOProps {
  title?: string;
  description?: string;
  canonicalPath?: string;
  noindex?: boolean;
}

export const SEO: React.FC<SEOProps> = ({
  title,
  description = SITE.description,
  canonicalPath = "",
  noindex = false,
}) => {
  const siteUrl = getSiteUrl();
  const fullTitle = title ? `${title} · ${SITE.name}` : `${SITE.name} — Live ETA prediction & platform conflict detection for Indian Railways`;
  const canonicalUrl = `${siteUrl}${canonicalPath.startsWith("/") ? canonicalPath : `/${canonicalPath}`}`;
  const ogImageUrl = `${siteUrl}/og.png`;

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      {noindex ? (
        <meta name="robots" content="noindex, nofollow" />
      ) : (
        <meta name="robots" content="index, follow" />
      )}
      <link rel="canonical" href={canonicalUrl} />

      {/* Open Graph */}
      <meta property="og:type" content="website" />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={canonicalUrl} />
      <meta property="og:image" content={ogImageUrl} />

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={ogImageUrl} />
    </Helmet>
  );
};
