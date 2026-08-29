import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { loginWithMockAuth, DEMO_USERS } from '@/mock/auth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { SEO } from '@/lib/seo';
import { SITE } from '@/config/site';
import { ArrowRight, KeyRound, Check } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const nextPath = searchParams.get('next') ? decodeURIComponent(searchParams.get('next')!) : '/dashboard';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [autofilled, setAutofilled] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError('Please enter both email and password.');
      return;
    }

    setIsLoading(true);
    try {
      await loginWithMockAuth(email, password);
      navigate(nextPath, { replace: true });
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Invalid credentials — try the demo login');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (demoEmail: string, demoPass: string, label: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
    setAutofilled(label);
    setTimeout(() => setAutofilled(null), 2000);
  };

  return (
    <div className="min-h-screen bg-bg text-text-main flex flex-col justify-between font-sans px-4 py-8">
      <SEO
        title="Sign in"
        description="Station login for RailTwin-X."
        noindex={true}
        canonicalPath="/login"
      />

      {/* Brand Header */}
      <header className="max-w-md mx-auto w-full flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-text-main font-mono font-bold text-sm tracking-tight hover:text-accent transition-colors">
          <span className="w-2.5 h-2.5 bg-accent inline-block rounded-none" />
          <span>{SITE.name}</span>
        </Link>
        <Link to="/" className="text-xs text-text-dim hover:text-text-main font-mono transition-colors">
          ← Back to home
        </Link>
      </header>

      {/* Main Login Panel — Max 380px per §7 */}
      <main className="max-w-[380px] mx-auto w-full my-auto">
        <div className="bg-panel border border-hairline p-6 shadow-xl space-y-5">
          <div className="space-y-1">
            <h1 className="text-lg font-bold text-text-main font-sans tracking-tight">
              Station login
            </h1>
            <p className="text-xs text-text-dim font-sans">
              Enter your division credentials to access the live digital twin.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3" noValidate>
            <div>
              <label className="block text-[11px] font-mono uppercase text-text-dim mb-1">
                Official Email
              </label>
              <Input
                type="email"
                value={email}
                onChange={e => {
                  setEmail(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="sm@cnb.railtwin.app"
                autoComplete="email"
                disabled={isLoading}
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-[11px] font-mono uppercase text-text-dim">
                  Password
                </label>
              </div>
              <Input
                type="password"
                value={password}
                onChange={e => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="••••••••"
                autoComplete="current-password"
                disabled={isLoading}
              />
            </div>

            {/* Field-level error under the form per §7 */}
            {error && (
              <div className="p-2.5 bg-danger/10 border border-danger text-danger text-xs font-sans">
                {error}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isLoading}
              className="w-full text-xs font-semibold gap-2 mt-2"
            >
              <span>Sign in</span>
              <ArrowRight className="w-3.5 h-3.5 stroke-[1.5]" />
            </Button>
          </form>

          {/* Demo Credentials Fast-Path per §7 */}
          <div className="pt-3 border-t border-hairline space-y-2">
            <div className="flex items-center justify-between text-[11px] font-mono text-text-dim">
              <span className="flex items-center gap-1">
                <KeyRound className="w-3 h-3 text-accent stroke-[1.5]" />
                <span>Demo Fast-Path</span>
              </span>
              {autofilled && (
                <span className="text-ok flex items-center gap-1 text-[10px]">
                  <Check className="w-3 h-3 stroke-[2]" /> {autofilled} filled
                </span>
              )}
            </div>

            <div className="space-y-1.5 font-mono text-xs max-h-48 overflow-y-auto no-scrollbar">
              {DEMO_USERS.map(demo => (
                <button
                  key={demo.id}
                  type="button"
                  onClick={() => handleQuickFill(demo.email, demo.password, demo.roleName)}
                  className="w-full p-2 bg-panel-2 hover:bg-hairline/60 border border-hairline text-left flex items-center justify-between transition-colors text-[11px]"
                >
                  <div className="truncate pr-2">
                    <div className="font-semibold text-text-main truncate">{demo.roleName}</div>
                    <div className="text-[10px] text-text-dim truncate">{demo.email}</div>
                  </div>
                  <span className="text-[9px] text-accent border border-accent/40 px-1.5 py-0.5 shrink-0">
                    Fill
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="text-center pt-2">
            <Link to="/" className="text-xs text-text-dim hover:text-text-main font-sans transition-colors">
              Need access? Request it on the home page →
            </Link>
          </div>
        </div>
      </main>

      {/* Safety Disclaimer Footer */}
      <footer className="text-center text-[11px] font-mono text-text-dim py-4">
        {SITE.disclaimer}
      </footer>
    </div>
  );
};
