/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class', // <-- ESTA LÍNEA ES CLAVE
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}