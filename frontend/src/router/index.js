import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus' // 记得引入提示组件

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login.vue')
  },
  {
    path: '/search',
    name: 'search',
    component: () => import('@/views/search.vue')
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/admin.vue'),
    meta: { requiresAdmin: true } // <--- 新增这行，给管理界面打上标记
  },
  {
    path: '/',
    redirect: '/search'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const role = localStorage.getItem('user_role') // <--- 获取当前用户的角色
  
  // 1. 如果没登录且去的不是登录页，踢回登录页
  if (to.name !== 'login' && !token) {
    next({ name: 'login' })
  } 
  // 2. 如果已经登录了还去登录页，引导到检索页
  else if (to.name === 'login' && token) {
    next({ name: 'search' })
  } 
  // 3. 核心拦截：如果去的页面需要管理员权限，但当前用户不是管理员
  else if (to.meta.requiresAdmin && role !== 'admin') {
    ElMessage.error('越权访问拦截：您没有系统控制台的访问权限')
    next({ name: 'search' }) // 强制踢回普通检索界面
  } 
  // 4. 其他正常放行
  else {
    next()
  }
})

export default router