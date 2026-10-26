// Vite settings. Vite is the tool that runs the app while we develop and builds it for release.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Dev proxy: any request to /api/... is passed on to the Python backend, so the browser
    // thinks frontend and backend are one website. (Only used by `npm run dev`.)
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  // Tests (npm test): run in "jsdom", a pretend browser inside Node.
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
})
