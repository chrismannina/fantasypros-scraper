/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'fantasy-blue': '#2563eb',
        'fantasy-green': '#059669',
        'fantasy-red': '#dc2626',
        'fantasy-purple': '#7c3aed',
      }
    },
  },
  plugins: [],
} 