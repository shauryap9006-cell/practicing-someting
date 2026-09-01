import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'block-mock-imports',
      enforce: 'pre',
      resolveId(id, importer) {
        if (id.includes('/mock/store') && importer && (importer.includes('/pages/') || importer.includes('\\pages\\'))) {
          throw new Error(`MOCK IMPORT BLOCKED: ${importer} — use lib/api.ts`);
        }
      },
    },
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('three') || id.includes('@react-three')) {
            return 'vendor-three';
          }
          if (id.includes('gsap') || id.includes('lenis')) {
            return 'vendor-motion';
          }
          if (id.includes('echarts')) {
            return 'echarts';
          }
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/') || id.includes('node_modules/react-router-dom/')) {
            return 'vendor-react';
          }
          if (id.includes('@tanstack/react-query') || id.includes('@tanstack/react-table') || id.includes('@tanstack/react-virtual')) {
            return 'vendor-tanstack';
          }
        },
      },
    },
  },
});
