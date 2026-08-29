import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { SEO } from '@/lib/seo';
import { SITE } from '@/config/site';
import { Button } from '@/components/ui/Button';
import { CheckCircle2, ArrowLeft, Play } from 'lucide-react';

export const ThanksPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-bg text-text-main font-sans flex flex-col justify-between selection:bg-accent selection:text-bg px-4 py-8">
      <SEO
        title="Request received"
        description="Station access request confirmation."
        noindex={true}
        canonicalPath="/thanks"
      />

      {/* Header */}
      <header className="max-w-md mx-auto w-full flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-mono font-bold text-sm text-text-main hover:text-accent transition-colors">
          <span className="w-2.5 h-2.5 bg-accent inline-block rounded-none" />
          <span>{SITE.name}</span>
        </Link>
      </header>

      {/* Main Confirmation Box */}
      <main className="max-w-md mx-auto w-full my-auto">
        <div className="bg-panel border border-hairline p-6 sm:p-8 space-y-6 text-center">
          <div className="w-12 h-12 bg-ok/10 border border-ok text-ok flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-6 h-6 stroke-[2]" />
          </div>

          <div className="space-y-2">
            <h1 className="text-xl font-bold font-sans tracking-tight text-text-main">
              Request received.
            </h1>
            <p className="text-xs text-text-dim font-sans leading-relaxed max-w-sm mx-auto">
              Your station access application has been recorded in our dispatch registry. We will verify your division credentials and reply within 2 working days.
            </p>
          </div>

          <div className="pt-4 border-t border-hairline flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/" className="w-full sm:w-auto">
              <Button variant="primary" size="md" className="w-full text-xs font-semibold gap-2">
                <span>Back to home</span>
              </Button>
            </Link>
            <Link to="/#hero-live-demo" className="w-full sm:w-auto">
              <Button variant="outline" size="md" className="w-full text-xs font-mono text-text-dim hover:text-text-main">
                <span>See it live →</span>
              </Button>
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center text-[11px] font-mono text-text-dim py-4">
        {SITE.disclaimer}
      </footer>
    </div>
  );
};
