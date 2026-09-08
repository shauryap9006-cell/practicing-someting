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
      'three': path.resolve(__dirname, '../node_modules/three/src/Three.js'),
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
          const cleanId = id.replace('\0', '').replace(/\\/g, '/');
          if (cleanId.includes('preload') || cleanId.includes('vite/')) {
            return 'vendor-react';
          }
          if (!cleanId.includes('node_modules')) {
            return;
          }
          if (
            cleanId.includes('node_modules/react/') ||
            cleanId.includes('node_modules/react-dom/') ||
            cleanId.includes('node_modules/react-router') ||
            cleanId.includes('node_modules/@tanstack/')
          ) {
            return 'vendor-react';
          }
          if (cleanId.includes('node_modules/lucide-react')) {
            return 'vendor-lucide';
          }
          if (cleanId.includes('node_modules/echarts') || cleanId.includes('node_modules/zrender')) {
            return 'vendor-echarts';
          }
          if (cleanId.includes('node_modules/@react-three/drei')) {
            return 'vendor-three-drei';
          }
          if (cleanId.includes('node_modules/@react-three/fiber')) {
            return 'vendor-three-fiber';
          }
          if (
            cleanId.includes('node_modules/three/src/math') ||
            cleanId.includes('node_modules/three/src/constants.js')
          ) {
            return 'vendor-three-math';
          }
          if (cleanId.includes('node_modules/three/src/renderers/shaders')) {
            return 'vendor-three-shaders';
          }
          if (cleanId.includes('node_modules/three')) {
            return 'vendor-three';
          }
        },
      },
    },
  },
});
