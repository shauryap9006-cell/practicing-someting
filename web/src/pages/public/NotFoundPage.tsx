import React from 'react';
import { Link } from 'react-router-dom';
import { getCurrentSession } from '@/mock/auth';
import { Button } from '@/components/ui/Button';
import { SEO } from '@/lib/seo';
import { SITE } from '@/config/site';
import { TrainTrack, ArrowRight } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  const session = getCurrentSession();

  return (
    <div className="min-h-screen bg-bg text-text-main font-sans flex flex-col justify-between selection:bg-accent selection:text-bg px-4 py-8">
      <SEO
        title="Page not found"
        description="The requested track was not found."
        noindex={true}
      />

      {/* Header */}
      <header className="max-w-md mx-auto w-full flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-mono font-bold text-sm text-text-main hover:text-accent transition-colors">
          <span className="w-2.5 h-2.5 bg-accent inline-block rounded-none" />
          <span>{SITE.name}</span>
        </Link>
      </header>

      {/* Main 404 Panel */}
      <main className="max-w-md mx-auto w-full my-auto text-center space-y-6">
        <div className="bg-panel border border-hairline p-8 space-y-4">
          <div className="text-6xl font-bold font-mono text-accent">
            404
          </div>

          <div className="space-y-1">
            <h1 className="text-lg font-bold font-sans text-text-main">
              This track doesn't exist.
            </h1>
            <p className="text-xs text-text-dim font-sans leading-relaxed">
              The page you requested is not on the network. Check the address, or head back.
            </p>
          </div>

          <div className="pt-4 border-t border-hairline flex flex-col sm:flex-row items-center justify-center gap-3">
            {session ? (
              <Link to="/dashboard" className="w-full sm:w-auto">
                <Button variant="primary" size="md" className="w-full text-xs font-semibold gap-2">
                  <span>Return to dashboard</span>
                  <ArrowRight className="w-3.5 h-3.5 stroke-[1.5]" />
                </Button>
              </Link>
            ) : (
              <Link to="/login" className="w-full sm:w-auto">
                <Button variant="primary" size="md" className="w-full text-xs font-semibold gap-2">
                  <span>Sign in</span>
                  <ArrowRight className="w-3.5 h-3.5 stroke-[1.5]" />
                </Button>
              </Link>
            )}

            <Link to="/" className="w-full sm:w-auto">
              <Button variant="outline" size="md" className="w-full text-xs font-mono text-text-dim hover:text-text-main">
                <span>Home</span>
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
