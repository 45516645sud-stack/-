import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { aiSearchPlugin } from './vite-ai-plugin.js';

export default defineConfig({
  plugins: [react(), aiSearchPlugin()],
  server: {
    proxy: {
      '/tourapi': {
        target: 'https://apis.data.go.kr',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/tourapi/, '/B551011/KorService2'),
      },
    },
  },
});
