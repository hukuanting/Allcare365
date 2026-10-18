import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react({ include: /\.[jt]sx?$/ })],
  build: { manifest: true },
  test: {
    environment: 'jsdom',
    // Bound concurrent DOM-heavy suites to avoid worker contention on dev machines.
    maxWorkers: 4,
    globals: true,
    setupFiles: ['./src/setupTests.js'],
    clearMocks: true,
  },
});
