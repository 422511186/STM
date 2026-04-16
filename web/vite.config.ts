import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/auth': {
        target: 'http://127.0.0.1:50051',
        changeOrigin: true,
      },
      '/tunnels': {
        target: 'http://127.0.0.1:50051',
        changeOrigin: true,
      },
      '/config': {
        target: 'http://127.0.0.1:50051',
        changeOrigin: true,
      },
      '/logs': {
        target: 'http://127.0.0.1:50051',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:50051',
        changeOrigin: true,
      },
    },
  },
})
