import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login.vue')
  },
  {
    path: '/search',
    name: 'search',
    component: () => import('@/views/Search.vue')
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/admin.vue'),
    meta: { requiresAdmin: true }
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
  const role = localStorage.getItem('user_role')

  if (to.name !== 'login' && !token) {
    next({ name: 'login' })
    return
  }

  if (to.name === 'login' && token) {
    next({ name: 'search' })
    return
  }

  if (to.meta.requiresAdmin && role !== 'admin') {
    ElMessage.error('当前账号没有后台控制台访问权限。')
    next({ name: 'search' })
    return
  }

  next()
})

export default router
