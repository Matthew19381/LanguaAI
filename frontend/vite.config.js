import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['logo.svg', 'icons/apple-touch-icon.png'],
      manifest: {
        name: 'LinguaAI — Nauka Języków',
        short_name: 'LinguaAI',
        description: 'Personalizowana nauka języków: lekcje, fiszki i ćwiczenia z powtórkami w odstępach.',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#111827',
        theme_color: '#4f46e5',
        lang: 'pl',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: '/icons/icon-maskable-192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
          { src: '/icons/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
        shortcuts: [
          { name: 'Ćwiczenia', short_name: 'Ćwiczenia', url: '/practice' },
          { name: 'Fiszki', short_name: 'Fiszki', url: '/flashcards' },
          { name: 'Dzisiejsza lekcja', short_name: 'Lekcja', url: '/lesson' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,woff2}'],
        navigateFallback: '/index.html',
        // Web Push handlers (push / notificationclick). Pulled into the generated
        // service worker so all the runtime caching below stays intact.
        importScripts: ['push-sw.js'],
        // API responses are cached read-only. Writes (answering exercises,
        // completing lessons) still need the network — see TASKS.md.
        runtimeCaching: [
          {
            // Exercise bank: the offline-friendliest content in the app —
            // items are stored data, not AI generation.
            urlPattern: ({ url }) => url.pathname.startsWith('/api/exercises/'),
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'exercises-cache',
              expiration: { maxEntries: 60, maxAgeSeconds: 60 * 60 * 24 * 7 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/lessons/'),
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'lessons-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/flashcards/'),
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'flashcards-cache',
              expiration: { maxEntries: 60, maxAgeSeconds: 60 * 60 * 12 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/stats/'),
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'stats-cache',
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 6 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Lesson / flashcard / dictation audio (edge-tts mp3)
            urlPattern: ({ url }) => url.pathname.startsWith('/audio/'),
            handler: 'CacheFirst',
            options: {
              cacheName: 'audio-cache',
              expiration: { maxEntries: 100, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      devOptions: {
        // Keep the service worker out of the way during development
        enabled: false,
      },
    }),
  ],
  server: {
    port: 5173,
    // Listen on all interfaces so the app can be opened from a phone on the
    // same Wi-Fi (http://<computer-ip>:5173).
    host: true,
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
  // `vite preview` (production build) needs the same proxy as dev, otherwise the
  // built app cannot reach the backend.
  preview: {
    port: 4173,
    host: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8001',
        changeOrigin: true,
      },
      '/audio': {
        target: process.env.VITE_API_URL || 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  },
  // Ensure proper handling of SPA routing in dev
  appType: 'spa'
})
