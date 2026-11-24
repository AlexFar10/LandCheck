/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// The repo-root .env is shared with the API.
const envDir = '..'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, envDir, '')
  // Dev only: proxy API calls to the local API, so the browser sees one origin (as in
  // production, where FastAPI serves the built app) and no CORS setup is needed.
  const apiTarget = `http://127.0.0.1:${env.PORT || '3000'}`
  return {
    plugins: [react()],
    envDir,
    // MapLibre's worker is an ES module (see src/maplibre-worker.ts).
    worker: { format: 'es' },
    server: {
      proxy: {
        '/api': apiTarget,
        '/health': apiTarget,
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test-setup.ts'],
    },
  }
})
