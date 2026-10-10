import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon.svg'],
      manifest: {
        name: 'Jaltaranga · Flood evacuation intelligence',
        short_name: 'Jaltaranga',
        description: 'Historical Yamuna flood replay and resident evacuation plans.',
        theme_color: '#f5f4ef',
        background_color: '#f5f4ef',
        display: 'standalone',
        start_url: '/command',
        icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' }],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,woff2,json,png,webmanifest}'],
        maximumFileSizeToCacheInBytes: 1_500_000,
        navigateFallbackDenylist: [/\.(?:pmtiles|png|tif|tiff|geojson)$/i],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.endsWith('.pmtiles'),
            handler: 'NetworkOnly',
          },
          {
            urlPattern: ({ request, url }) => request.destination === 'font' || /\.(?:woff2?)$/i.test(url.pathname),
            handler: 'CacheFirst',
            options: { cacheName: 'jaltaranga-fonts', expiration: { maxEntries: 12, maxAgeSeconds: 31_536_000 } },
          },
        ],
      },
    }),
  ],
  server: { fs: { allow: ['..'] } },
  build: {
    target: 'es2022',
    sourcemap: true,
    manifest: true,
    rollupOptions: { output: { manualChunks: (id) => /node_modules[\\/](?:maplibre-gl|pmtiles|@protomaps)[\\/]/.test(id) ? 'maplibre' : undefined } },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    include: ['src/**/*.test.ts'],
    coverage: { reporter: ['text', 'html'], include: ['src/lib/**', 'src/data/**'] },
  },
});
