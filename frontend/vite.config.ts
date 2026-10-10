import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // En `npm run dev`, las llamadas a /api van al backend a través de NGINX.
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
})
