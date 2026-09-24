import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    global: 'window', // Fix lỗi "Uncaught ReferenceError: global is not defined" của sockjs-client
  },
});