import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy de /api/* en desarrollo:
//   - VITE_API_TARGET=http://localhost:5050  → Flask local (python server.py)
//   - sin variable → producción (solo lectura práctica; las keys viven en el server)
const API_TARGET = process.env.VITE_API_TARGET
  || 'https://supply-chain-for-ai-production.up.railway.app'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    css: false,
  },
})
