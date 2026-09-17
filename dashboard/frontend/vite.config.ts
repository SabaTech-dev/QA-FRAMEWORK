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
    allowedHosts: ['qa.sabatech.dev', 'qa-framework.sabatech.dev', 'api.qa.sabatech.dev', 'localhost'],
    proxy: {
      '/api': {
        // BACKEND_URL: injected at runtime by preview deployments (Coolify
        // env on the frontend container) to reach the paired backend preview.
        target: process.env.BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
