/// <reference types="vitest" />
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'path';

export default defineConfig({
  plugins: [svelte()],
  root: 'article',
  publicDir: resolve(__dirname, 'article/data'),
  build: {
    outDir: resolve(__dirname, 'dist-article'),
    emptyOutDir: true,
  },
  server: { port: 5174 },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['article/**/*.test.ts'],
  },
});
