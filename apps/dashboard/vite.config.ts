import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const isDev = mode === 'development'
  
  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@citadel/widget-library': path.resolve(__dirname, '../../packages/widget-library/src/index.ts'),
      },
    },
    server: {
      proxy: isDev ? {
        '/auth': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/v1': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        }
      } : undefined
    },
    define: {
      __API_URL__: JSON.stringify(
        isDev 
          ? ''  // Uses proxy in dev
          : 'https://api.citadelsdk.com'  // Production API
      ),
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
      rollupOptions: {
        external: ['react', 'react-dom'],
      }
    }
  }
})
