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

export function fetchVehicleImages(vehicleId, galleryToken, params = {}) {
  return request({
    url: '/gallery/vehicle-images',
    method: 'get',
    params: {
      vehicle_id: vehicleId,
      gallery_token: galleryToken,
      page: params.page || 1,
      page_size: params.pageSize || 36
    }
  })
}
