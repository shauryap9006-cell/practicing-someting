import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { App } from './App';
import { initAnalytics } from './lib/analytics';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 5000, // 5s live tick integration per §3.1
      staleTime: 3000,
      retry: 1,
    },
  },
});

// Initialize analytics if enabled & consented
initAnalytics();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
          <Toaster
            theme="dark"
            position="top-right"
            toastOptions={{
              style: {
                background: 'var(--color-panel)',
                border: '1px solid var(--color-hairline)',
                color: 'var(--color-text)',
                borderRadius: '2px',
                fontFamily: 'IBM Plex Mono, monospace',
                fontSize: '12px',
              },
            }}
          />
        </BrowserRouter>
      </QueryClientProvider>
    </HelmetProvider>
  </React.StrictMode>
);
