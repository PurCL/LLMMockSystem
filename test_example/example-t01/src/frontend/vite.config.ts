import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '')

  // Default to localhost (local dev) if not provided (e.g. by Docker)
  const apiTarget = env.VITE_API_TARGET || 'http://127.0.0.1:8000'
  const wsTarget = env.VITE_WS_TARGET || 'ws://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      watch: {
        usePolling: true,
      },
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/ws': {
          target: wsTarget,
          changeOrigin: true,
          rewrite: (path) => '/api/collaboration' + path,
          ws: true,
        },
      },
    },
  }
})
