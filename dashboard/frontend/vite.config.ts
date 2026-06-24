import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,
    port: 3000,
    allowedHosts: ['qa.sabatech.dev', 'qa-framework.sabatech.dev', 'localhost'],
    proxy: {
      '/api': {
        // Inside Docker the backend is reachable at http://backend:8000 (service name).
        // For local dev it runs on http://localhost:8000. Override via API_PROXY_TARGET.
        target: process.env.API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})