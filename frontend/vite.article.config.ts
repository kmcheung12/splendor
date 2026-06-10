/// <reference types="vitest" />
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'path';
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [svelte(), visualizer({ filename: 'dist-article/stats.html', gzipSize: true })],
  root: 'article',
  publicDir: resolve(__dirname, 'article/data'),
  build: {
    outDir: resolve(__dirname, 'dist-article'),
    emptyOutDir: true,
  },
  server: { port: 5174 },
  resolve: {
    conditions: ['browser'],
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['**/*.test.ts'],
  },
});
