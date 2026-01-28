import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const service = axios.create({
  // 注意：这里假设你的后端开在 8000 端口
  baseURL: 'http://localhost:8000/api/v1', 
  timeout: 10000 // 请求超时时间
})

// 响应拦截器
service.interceptors.response.use(
  response => {
    const res = response.data
    // 后端约定：code 200 代表成功 [cite: 303]
    if (res.code !== 200) {
      ElMessage.error(res.message || 'Error')
      return Promise.reject(new Error(res.message || 'Error'))
    } else {
      return res
    }
  },
  error => {
    console.error('err' + error)
    ElMessage.error(error.message || 'Request Failed')
    return Promise.reject(error)
  }
)

export default service