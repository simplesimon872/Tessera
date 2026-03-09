import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg:       '#0A0A0B',
        surface:  '#111113',
        border:   '#1E1E22',
        muted:    '#888890',
        primary:  '#F0F0F0',
        accent:   '#E8FF47',
        sealed:   '#4AFF91',
        failed:   '#FF4A4A',
      },
      fontFamily: {
        sans: ['var(--font-syne)', 'sans-serif'],
        mono: ['var(--font-plex)', 'monospace'],
      },
    },
  },
  plugins: [],
}

export default config
