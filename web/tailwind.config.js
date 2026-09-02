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
        'bg-0': 'var(--bg-0)',
        'bg-1': 'var(--bg-1)',
        'bg-2': 'var(--bg-2)',
        'bg-3': 'var(--bg-3)',
        line: 'var(--line)',
        'line-strong': 'var(--line-strong)',
        'text-1': 'var(--text-1)',
        'text-2': 'var(--text-2)',
        'text-3': 'var(--text-3)',
        'aspect-clear': 'var(--aspect-clear)',
        'aspect-caution': 'var(--aspect-caution)',
        'aspect-restrict': 'var(--aspect-restrict)',
        'aspect-signal': 'var(--aspect-signal)',
        'tint-clear': 'var(--tint-clear)',
        'tint-caution': 'var(--tint-caution)',
        'tint-restrict': 'var(--tint-restrict)',
        'tint-signal': 'var(--tint-signal)',

        // Legacy compatibility
        bg: 'var(--bg-0)',
        panel: 'var(--bg-1)',
        'panel-2': 'var(--bg-2)',
        hairline: 'var(--line)',
        'text-main': 'var(--text-1)',
        'text-dim': 'var(--text-2)',
        accent: 'var(--aspect-caution)',
        ok: 'var(--aspect-clear)',
        warn: 'var(--aspect-caution)',
        danger: 'var(--aspect-restrict)',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        sans: ['Inter', 'IBM Plex Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'IBM Plex Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      borderRadius: {
        none: '0px',
        DEFAULT: '6px',
        sm: '6px',
        md: '10px',
        lg: '14px',
        card: '10px',
        modal: '14px',
      },
      transitionTimingFunction: {
        track: 'cubic-bezier(0.2, 0, 0, 1)',
      },
      keyframes: {
        'amber-flash': {
          '0%': { backgroundColor: 'rgba(245, 165, 36, 0.35)', color: '#F5A524' },
          '100%': { backgroundColor: 'transparent' },
        },
        'track-sweep': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'flash-update': 'amber-flash 400ms ease-out',
        'track-sweep': 'track-sweep 1.6s infinite linear',
      },
    },
  },
  plugins: [],
};
