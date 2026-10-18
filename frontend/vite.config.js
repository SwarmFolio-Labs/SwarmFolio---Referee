import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// The API (api.py) runs on :8000 and serves every route under /api too, so dev just proxies /api.
// For a separate deployment (e.g. Vercel + Render), set VITE_API_URL to the API's address
// (https://swarmfolio-api.onrender.com) at build time; the app then calls <VITE_API_URL>/api/...
export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), 'VITE_'), ...process.env }
  const apiUrl = (env.VITE_API_URL || '').trim().replace(/\/+$/, '')
  const define = apiUrl && !env.VITE_API_BASE
    ? { 'import.meta.env.VITE_API_BASE': JSON.stringify(`${apiUrl}/api`) }
    : {}

  return {
    plugins: [react()],
    define,
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: process.env.API_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
