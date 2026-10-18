import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API (api.py) runs on :8000 and serves every route under /api too, so dev just proxies /api.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
