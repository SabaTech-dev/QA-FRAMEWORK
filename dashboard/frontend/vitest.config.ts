import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  // React 18.3 resuelve la build dev/prod leyendo process.env.NODE_ENV en
  // tiempo de ejecucion. Si el shell o CI trae NODE_ENV=production, React
  // carga la build de produccion y @testing-library/react lanza
  // "act() is not supported in production builds". Lo forzamos a 'test' y
  // inlineamos react/react-dom para que Vite transforme ese dispatch.
  define: {
    'process.env.NODE_ENV': JSON.stringify('test'),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    exclude: ['node_modules', 'dist', 'e2e'],
    setupFiles: ['./src/test/setup.ts'],
    server: {
      deps: {
        inline: [/react/, /react-dom/, /scheduler/],
      },
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.*', 'src/test/**', 'src/vite-env.d.ts', 'src/main.tsx'],
    },
  },
})
