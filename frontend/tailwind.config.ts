import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0d1117',
          surface: '#161b22',
          panel: '#1a1a2e',
          border: '#30363d',
          'border-light': '#484f58',
          text: '#e6edf3',
          'text-muted': '#8b949e',
          'text-dim': '#6e7681',
        },
        accent: {
          yellow: '#ecad0a',
          blue: '#209dd7',
          purple: '#753991',
        },
        price: {
          up: '#3fb950',
          down: '#f85149',
          'up-bg': 'rgba(63, 185, 80, 0.15)',
          'down-bg': 'rgba(248, 81, 73, 0.15)',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'flash-green': 'flashGreen 500ms ease-out',
        'flash-red': 'flashRed 500ms ease-out',
      },
      keyframes: {
        flashGreen: {
          '0%': { backgroundColor: 'rgba(63, 185, 80, 0.3)' },
          '100%': { backgroundColor: 'transparent' },
        },
        flashRed: {
          '0%': { backgroundColor: 'rgba(248, 81, 73, 0.3)' },
          '100%': { backgroundColor: 'transparent' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
