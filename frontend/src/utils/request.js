import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: 'http://localhost:8000/api/v1', 
  timeout: 10000 
})

service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    console.error('Request Error:', error)
    return Promise.reject(error)
  }
)

service.interceptors.response.use(
  response => {
    const res = response.data
    
    if (res.access_token) {
      return res
    }
    
    if (res.code !== 200) {
      ElMessage.error(res.message || 'Error')
      return Promise.reject(new Error(res.message || 'Error'))
    } else {
      return res
    }
  },
  error => {
    console.error('Response Error:', error)
    if (error.response && error.response.status === 401) {
      ElMessage.error('身份凭证已过期或无效，请重新验证')
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    } else {
      ElMessage.error(error.message || 'Request Failed')
    }
    return Promise.reject(error)
  }
)

export default service