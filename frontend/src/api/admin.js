import request from '@/utils/request'

export function fetchAuditLogs(page = 1, size = 15) {
  return request({ url: '/admin/logs', method: 'get', params: { page, size } })
}

export function syncGalleryData() {
  return request({ url: '/admin/gallery/sync', method: 'post' })
}

export function clearGalleryData() {
  return request({ url: '/admin/gallery/clear', method: 'post' })
}

export function rebuildGalleryData() {
  return request({ url: '/admin/gallery/rebuild', method: 'post' })
}

export function fetchGalleryStatus() {
  return request({ url: '/admin/gallery/status', method: 'get' })
}

export function fetchSystemStats() {
  return request({ url: '/admin/gallery/stats', method: 'get' })
}

export function fetchSysConfig() {
  return request({ url: '/admin/config', method: 'get' })
}

export function updateSysConfig(data) {
  return request({ url: '/admin/config', method: 'post', data })
}

export function fetchUserList() {
  return request({ url: '/admin/users', method: 'get' })
}

export function createNewUser(data) {
  return request({ url: '/admin/users', method: 'post', data })
}

export function removeUser(userId) {
  return request({ url: `/admin/users/${userId}`, method: 'delete' })
}