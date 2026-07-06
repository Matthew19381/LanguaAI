import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react()
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8001',
        changeOrigin: true,
      },
      '/audio': {
        target: process.env.VITE_API_URL || 'http://localhost:8001',
        changeOrigin: true,
      }
    },
    // Handle client-side routing - serve index.html for all non-asset routes
    fs: {
      strict: false
    }
  },
  // Ensure proper handling of SPA routing in dev
  appType: 'spa'
})
