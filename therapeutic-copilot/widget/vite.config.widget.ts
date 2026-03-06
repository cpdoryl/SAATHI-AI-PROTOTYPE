import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Widget build config — produces a single self-contained bundle (~50KB target)
 * Output: dist/widget.bundle.js — served by FastAPI /api/v1/widget/bundle.js
 */
export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: 'src/widget.ts',
      name: 'SaathiWidget',
      fileName: () => 'widget.bundle.js',
      formats: ['iife'],  // IIFE for browser global injection
    },
    rollupOptions: {
      external: [],       // Bundle everything — no external deps
    },
    outDir: 'dist',
    minify: 'esbuild',
    sourcemap: false,
  },
  define: {
    'process.env.NODE_ENV': '"production"',
  },
})
