import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { loginWithMockAuth, DEMO_USERS } from '@/mock/auth';
import { SEO } from '@/lib/seo';
import { SITE } from '@/config/site';
import { ArrowRight, KeyRound, Check, ShieldCheck } from 'lucide-react';

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
    <div className="min-h-screen bg-[#0A0B0D] text-[#E9EBEE] flex flex-col justify-between font-mono select-none px-4 py-8">
      <SEO
        title="Sign in · RailTwin-X"
        description="Station controller authentication login for RailTwin-X."
        noindex={true}
        canonicalPath="/login"
      />

      {/* Brand Header */}
      <header className="max-w-md mx-auto w-full flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-bold text-sm tracking-tight hover:text-[#F5A524] transition-colors">
          <span className="w-2.5 h-2.5 rounded-full bg-[#F5A524] shadow-[0_0_8px_rgba(245,165,36,0.6)] animate-pulse" />
          <span className="text-[#E9EBEE]">RailTwin<span className="text-[#F5A524]">-X</span></span>
        </Link>
        <Link to="/" className="text-xs text-[#A3ABB6] hover:text-[#E9EBEE] transition-colors">
          ← Back to home
        </Link>
      </header>

      {/* Main Login Panel */}
      <main className="max-w-[400px] mx-auto w-full my-auto">
        <div className="bg-[#101216] border border-[#23272F] rounded-lg p-6 shadow-2xl space-y-5">
          <div className="space-y-1">
            <h1 className="text-lg font-bold text-[#E9EBEE] tracking-tight font-display uppercase">
              STATION CONTROLLER SIGN-IN
            </h1>
            <p className="text-xs font-sans text-[#A3ABB6]">
              Enter divisional credentials or select a 1-click simulation persona.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label className="block text-[10px] uppercase text-[#6B7480] mb-1">
                Official Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => {
                  setEmail(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="sm@cnb.railtwin.app"
                autoComplete="email"
                disabled={isLoading}
                className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm py-2 px-3 text-xs text-[#E9EBEE] placeholder-[#6B7480]"
              />
            </div>

            <div>
              <label className="block text-[10px] uppercase text-[#6B7480] mb-1">
                Security Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="••••••••"
                autoComplete="current-password"
                disabled={isLoading}
                className="w-full bg-[#0A0B0D] border border-[#23272F] focus:border-[#F5A524] rounded-sm py-2 px-3 text-xs text-[#E9EBEE] placeholder-[#6B7480]"
              />
            </div>

            {error && (
              <div className="p-2.5 bg-[rgba(244,80,106,0.13)] border border-[#F4506A]/40 text-[#F4506A] text-xs rounded-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-[#F5A524] hover:bg-[#F5A524]/90 text-[#0A0B0D] font-bold text-xs rounded-sm transition-colors flex items-center justify-center gap-2 shadow-sm"
            >
              <span>{isLoading ? 'Authenticating...' : 'Access Control Room'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Fill Accounts */}
          <div className="pt-4 border-t border-[#23272F] space-y-2">
            <span className="text-[10px] uppercase text-[#6B7480] block">
              1-Click Role Personas
            </span>

            <div className="grid grid-cols-2 gap-2">
              {DEMO_USERS.map(u => (
                <button
                  key={u.role}
                  type="button"
                  onClick={() => handleQuickFill(u.email, u.password, u.name)}
                  className="p-2 bg-[#0A0B0D] border border-[#23272F] hover:border-[#F5A524] rounded-sm text-left transition-colors"
                >
                  <div className="font-bold text-[11px] text-[#E9EBEE]">{u.role.replace('_', ' ').toUpperCase()}</div>
                  <div className="text-[9px] text-[#6B7480] truncate">{u.name}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-md mx-auto w-full text-center text-[10px] text-[#6B7480]">
        <span>INDIAN RAILWAYS · ASPECT DISPATCH OS v3.0</span>
      </footer>
    </div>
  );
};
