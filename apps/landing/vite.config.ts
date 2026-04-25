import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const isDev = mode === 'development'

  return {
    plugins: [react(), tailwindcss()],
    build: {
      outDir: 'dist',
    },
    server: {
      proxy: isDev ? {
        '/demo': {
          target: 'http://localhost:5174',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/demo/, ''),
        },
      } : undefined,
    },
  }
})
