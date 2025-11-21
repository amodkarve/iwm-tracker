import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        // Use backend service name in Docker, localhost for local dev
        target: process.env.VITE_API_URL || (process.env.DOCKER ? 'http://backend:8000' : 'http://localhost:8000'),
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },
})

