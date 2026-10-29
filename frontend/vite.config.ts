/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // En `npm run dev`, las llamadas a /api van al backend a través de NGINX.
    proxy: {
      // ws: también reenvía el WebSocket del motor en tiempo real (PB-07).
      '/api': { target: 'http://localhost:8080', ws: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
