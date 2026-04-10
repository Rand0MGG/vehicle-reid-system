import request from '@/utils/request'

export function fetchAuditLogs(page = 1, size = 15) {
  return request({ url: '/admin/logs', method: 'get', params: { page, size } })
}

export function startGallerySync() {
  return request({ url: '/admin/gallery/sync', method: 'post' })
}

export function clearGalleryRecords() {
  return request({ url: '/admin/gallery/clear', method: 'post' })
}

export function rebuildGalleryRecords() {
  return request({ url: '/admin/gallery/rebuild', method: 'post' })
}

export function fetchGalleryTaskStatus() {
  return request({ url: '/admin/gallery/status', method: 'get' })
}

export function openGalleryFolder() {
  return request({ url: '/admin/gallery/open-folder', method: 'post' })
}

export function fetchAdminOverview() {
  return request({ url: '/admin/overview', method: 'get' })
}

export function fetchSystemConfig() {
  return request({ url: '/admin/config', method: 'get' })
}

export function saveSystemConfig(data) {
  return request({ url: '/admin/config', method: 'post', data })
}

export function fetchModelState() {
  return request({ url: '/admin/models', method: 'get' })
}

export function applyCurrentModel(data) {
  return request({ url: '/admin/models/select', method: 'post', data })
}

export function fetchUsers() {
  return request({ url: '/admin/users', method: 'get' })
}

export function createUser(data) {
  return request({ url: '/admin/users', method: 'post', data })
}

export function updateUser(userId, data) {
  return request({ url: `/admin/users/${userId}`, method: 'patch', data })
}

export function deleteUser(userId) {
  return request({ url: `/admin/users/${userId}`, method: 'delete' })
}
