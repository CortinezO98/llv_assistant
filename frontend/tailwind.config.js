/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0faf4',
          100: '#dcf4e6',
          200: '#bbe8ce',
          300: '#88d5ad',
          400: '#4fb883',
          500: '#2a9d63',
          600: '#1B5E3F',
          700: '#165233',
          800: '#12422a',
          900: '#0f3623',
        },
      },
      fontFamily: {
        sans: ['"DM Sans"', 'sans-serif'],
        display: ['"Syne"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}
