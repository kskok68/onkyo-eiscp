import { defineConfig } from 'vite';
import aurelia from '@aurelia/vite-plugin';
import { nodePolyfills } from 'vite-plugin-node-polyfills';
import { viteSingleFile } from 'vite-plugin-singlefile';

export default defineConfig({
  base: '/onkyo-eiscp/',
  server: {
    open: !process.env.CI,
    port: 9000,
    fs: {
      allow: ['..'],
    },
  },
  esbuild: {
    target: 'es2022',
  },
  plugins: [
    aurelia({
      useDev: true,
    }),
    nodePolyfills(),
    viteSingleFile(),
  ],
});
