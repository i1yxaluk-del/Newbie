import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        rewrite: path => path.replace(/^\/uploads/, '/api/uploads')
      }
    }
  },
  build: { outDir: 'dist' }
})
