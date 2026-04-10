import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL?.trim() || '/api/v1',
  timeout: 10000
})

service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => {
    console.error('Request Error:', error)
    return Promise.reject(error)
  }
)

service.interceptors.response.use(
  (response) => {
    const res = response.data

    if (res.access_token) {
      return res
    }

    if (res.code !== 200) {
      ElMessage.error(res.message || '请求失败，请稍后重试。')
      return Promise.reject(new Error(res.message || '请求失败，请稍后重试。'))
    }

    return res
  },
  (error) => {
    console.error('Response Error:', error)
    const responseMessage =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      '请求失败，请稍后重试。'

    if (error.response && error.response.status === 401) {
      ElMessage.error('身份凭证已过期或无效，请重新登录。')
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_role')
      if (router.currentRoute.value.name !== 'login') {
        router.push({ name: 'login' }).catch(() => {})
      }
    } else {
      ElMessage.error(responseMessage)
    }

    error.message = responseMessage
    return Promise.reject(error)
  }
)

export default service
