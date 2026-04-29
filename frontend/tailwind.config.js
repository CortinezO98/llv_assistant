/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#faf8f5',
          100: '#f5f1eb',
          200: '#e8ddd0',
          300: '#d4c4a8',
          400: '#c6a96b',
          500: '#b8943a',
          600: '#0b4c45',
          700: '#093d38',
          800: '#072e2b',
          900: '#051f1e',
        },
        gold: {
          400: '#d4b896',
          500: '#c6a96b',
          600: '#b8943a',
        },
        cream: '#F5F1EB',
      },
      fontFamily: {
        sans:    ['"DM Sans"', 'sans-serif'],
        display: ['"Syne"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}
