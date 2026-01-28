import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// --- 新增内容 ---
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
// ----------------

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus) // 启用 Element Plus
app.mount('#app')