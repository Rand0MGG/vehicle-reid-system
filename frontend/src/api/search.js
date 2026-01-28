import request from '@/utils/request'

export function searchVehicle(data) {
  return request({
    url: '/search',
    method: 'post',
    data: data, // data 必须是 FormData 对象
    // 显式声明 multipart/form-data，虽然 axios 传入 FormData 时通常会自动识别
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}