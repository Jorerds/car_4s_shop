// Vite 配置：多入口构建——顾客端 H5（index.html）与管理端（admin/index.html）
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 管理端 SPA 回退中间件：history 模式下刷新 /admin/xxx 时返回管理端入口，
// 否则 Vite 默认回退到 index.html（顾客端入口），导致管理端刷新空白
function adminSpaFallback() {
  return {
    name: 'admin-spa-fallback',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        // 仅处理 /admin 前缀且未命中静态资源（含扩展名）的请求
        if (req.url?.startsWith('/admin') && !req.url.split('?')[0].includes('.')) {
          req.url = '/admin/index.html'
        }
        next()
      })
    }
  }
}

export default defineConfig({
  plugins: [vue(), adminSpaFallback()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    rollupOptions: {
      input: {
        h5: fileURLToPath(new URL('./index.html', import.meta.url)),
        admin: fileURLToPath(new URL('./admin/index.html', import.meta.url))
      }
    }
  },
  server: {
    // 开发服务端口：5173 常被 Windows/Hyper-V 动态保留段占用，改用 5273 空档
    port: 5273,
    // 开发环境代理到本地 FastAPI（/uploads 图片直出、/exports 报表导出文件）
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/uploads': 'http://127.0.0.1:8000',
      '/exports': 'http://127.0.0.1:8000'
    }
  }
})
