import animate from 'tailwindcss-animate'

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#050811', sidebar: '#07091a', accent: '#60a5fa', success: '#34d399',
        warning: '#fbbf24', danger: '#f87171', foreground: '#f1f5f9', muted: '#94a3b8', border: '#1e293b',
      },
      fontFamily: { sans: ['Inter', 'sans-serif'], heading: ['Syne', 'sans-serif'], mono: ['IBM Plex Mono', 'monospace'] },
      borderRadius: { xl: '0.9rem' },
    },
  },
  plugins: [animate],
}
