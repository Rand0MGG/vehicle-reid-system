import request from '@/utils/request'

export function fetchPublicModels() {
  return request({ url: '/models/public', method: 'get' })
}

export function searchVehicle(data) {
  return request({
    url: '/search',
    method: 'post',
    data,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
