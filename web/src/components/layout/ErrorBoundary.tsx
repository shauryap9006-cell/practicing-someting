import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <main role="alert" aria-live="assertive" className="min-h-screen bg-[#0A0B0D] text-[#E9EBEE] p-8 font-mono">
        <h1 className="text-lg font-bold uppercase">Operational module unavailable</h1>
        <p className="mt-2 text-sm text-[#A3ABB6]">
          The page failed to render safely. Reload the page or return to the dashboard.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-5 px-3 py-2 bg-[#F5A524] text-[#0A0B0D] font-bold text-xs rounded-sm"
        >
          Reload module
        </button>
      </main>
    );
  }
}
