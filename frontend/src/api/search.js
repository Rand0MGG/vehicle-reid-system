import request from '@/utils/request'

export function fetchPublicModels() {
  return request({ url: '/models/public', method: 'get' })
}

export function searchVehicle(data, options = {}) {
  return request({
    url: '/search',
    method: 'post',
    data,
    timeout: options.deepThinking ? 120000 : 30000,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
