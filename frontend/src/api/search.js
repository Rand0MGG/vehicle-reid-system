import request from '@/utils/request'

export function searchVehicle(data) {
  return request({
    url: '/search',
    method: 'post',
    data,
    // 显式声明 multipart/form-data，避免上传查询图像时被错误编码。
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
