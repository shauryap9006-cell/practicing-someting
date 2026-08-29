import React from 'react';
import { Link } from 'react-router-dom';
import { SEO } from '@/lib/seo';
import { SITE } from '@/config/site';
import { ArrowLeft, Shield } from 'lucide-react';

export const PrivacyPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-bg text-text-main font-sans flex flex-col justify-between selection:bg-accent selection:text-bg">
      <SEO
        title="Privacy Policy"
        description="What RailTwin-X collects, what it doesn't, and how anonymized analytics work."
        canonicalPath="/privacy"
      />

      {/* Header */}
      <header className="border-b border-hairline py-4 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-mono font-bold text-sm text-text-main hover:text-accent transition-colors">
            <span className="w-2 h-2 bg-accent inline-block" />
            <span>{SITE.name}</span>
          </Link>
          <Link to="/" className="text-xs font-mono text-text-dim hover:text-text-main flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5 stroke-[1.5]" />
            <span>Home</span>
          </Link>
        </div>
      </header>

      {/* Content: Max-width 68ch per §15 */}
      <main className="max-w-[68ch] mx-auto w-full px-4 py-12 space-y-8 text-xs sm:text-[13px] leading-relaxed">
        <div className="space-y-2 border-b border-hairline pb-6">
          <div className="text-xs font-mono text-accent uppercase tracking-wider">
            Legal & Telemetry
          </div>
          <h1 className="text-2xl font-bold font-sans tracking-tight text-text-main">
            Privacy Policy
          </h1>
          <p className="text-xs text-text-dim font-mono">
            Effective Date: August 2026 · Smart India Hackathon Build
          </p>
        </div>

        <section className="space-y-3">
          <h2 className="text-base font-bold font-sans text-text-main">
            1. Who We Are
          </h2>
          <p className="text-text-dim">
            RailTwin-X is an open-source decision-support digital twin created for Indian Railways station operations under {SITE.hackathon} ({SITE.problemStatement}). This platform is maintained by the {SITE.teamName}.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-base font-bold font-sans text-text-main">
            2. Data We Collect & Store
          </h2>
          <p className="text-text-dim">
            RailTwin-X operates under strict privacy-first principles. We do not collect personal identifiers, track across third-party websites, or sell any telemetry:
          </p>
          <ul className="space-y-2 pl-4 list-disc text-text-dim font-sans">
            <li>
              <strong className="text-text-main">Local Storage Tokens:</strong> Your browser stores theme preferences (<code className="font-mono text-accent">rtx-theme</code>), telemetry consent choices (<code className="font-mono text-accent">rtx-consent</code>), and your local 12-hour session credentials (<code className="font-mono text-accent">rtx-session</code>).
            </li>
            <li>
              <strong className="text-text-main">Access Requests:</strong> Station access requests submitted through our form are processed for access provisioning and stored in secured test stores.
            </li>
            <li>
              <strong className="text-text-main">Cookieless Analytics:</strong> If enabled and explicitly consented to, we use open-source, cookieless Umami analytics to count aggregate page views and operational sign-off counts without any IP addresses, unique identifiers, or persistent cookies. Analytics is shipped <strong className="text-text-main">disabled by default</strong> in this build.
            </li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-base font-bold font-sans text-text-main">
            3. What We Never Do
          </h2>
          <ul className="space-y-1.5 pl-4 list-disc text-text-dim">
            <li>We never serve advertisements.</li>
            <li>We never sell or monetize operational or user data.</li>
            <li>We never perform cross-site tracking or fingerprinting.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-base font-bold font-sans text-text-main">
            4. Contact & Compliance
          </h2>
          <p className="text-text-dim">
            For questions regarding this privacy policy or to request data erasure, contact our dispatch office:
          </p>
          <div className="p-3 bg-panel border border-hairline font-mono text-xs text-text-main space-y-1">
            <div>{SITE.teamName}</div>
            <div>{SITE.address}</div>
            <div>Email: <a href={`mailto:${SITE.email}`} className="text-accent underline">{SITE.email}</a></div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-hairline py-4 px-4 text-center text-[11px] font-mono text-text-dim">
        {SITE.disclaimer}
      </footer>
    </div>
  );
};
