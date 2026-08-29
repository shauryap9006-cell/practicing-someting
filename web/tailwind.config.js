/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        panel: 'var(--color-panel)',
        'panel-2': 'var(--color-panel-2)',
        hairline: 'var(--color-hairline)',
        'text-main': 'var(--color-text)',
        'text-dim': 'var(--color-text-dim)',
        accent: 'var(--color-accent)',
        ok: 'var(--color-ok)',
        warn: 'var(--color-warn)',
        danger: 'var(--color-danger)',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      borderRadius: {
        none: '0px',
        DEFAULT: '0px',
        sm: '2px',
        md: '2px',
        lg: '3px',
      },
      keyframes: {
        'amber-flash': {
          '0%': { backgroundColor: 'rgba(255, 178, 36, 0.35)', color: '#FFB224' },
          '100%': { backgroundColor: 'transparent' },
        },
      },
      animation: {
        'flash-update': 'amber-flash 400ms ease-out',
      },
    },
  },
  plugins: [],
};
