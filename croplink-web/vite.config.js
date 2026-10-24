import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        // Three.js is large; keep it in its own lazily-loaded chunk.
        manualChunks: { three: ['three'] },
      },
    },
  },
});
