import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
  const proxyTarget = env.VITE_DEV_PROXY_TARGET || 'http://localhost:8000'

  return {
    envDir: '..',
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src')
      }
    },
    server: {
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true
        },
        '/static': {
          target: proxyTarget,
          changeOrigin: true
        }
      }
    }
  }
})
