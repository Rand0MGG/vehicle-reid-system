import request from '@/utils/request'

export function fetchAuditLogs(page = 1, size = 15) {
  return request({ url: '/admin/logs', method: 'get', params: { page, size } })
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

export function fetchModelProfiles() {
  return request({ url: '/admin/model-profiles', method: 'get' })
}

export function createModelProfile(data) {
  return request({ url: '/admin/model-profiles', method: 'post', data })
}

export function updateModelProfile(profileId, data) {
  return request({ url: `/admin/model-profiles/${profileId}`, method: 'patch', data })
}

export function deleteModelProfile(profileId) {
  return request({ url: `/admin/model-profiles/${profileId}`, method: 'delete' })
}

export function publishModelProfile(profileId, isPublic) {
  return request({ url: `/admin/model-profiles/${profileId}/publish`, method: 'post', data: { is_public: isPublic } })
}

export function buildModelFeatures(profileId, rebuild = false) {
  return request({ url: `/admin/model-profiles/${profileId}/features/build`, method: 'post', data: { rebuild } })
}

export function clearModelFeatures(profileId) {
  return request({ url: `/admin/model-profiles/${profileId}/features`, method: 'delete' })
}

export function fetchModelFeatureStatus(profileId) {
  return request({ url: `/admin/model-profiles/${profileId}/features/status`, method: 'get' })
}

export function fetchGalleryImages(page = 1, size = 20) {
  return request({ url: '/admin/gallery/images', method: 'get', params: { page, size } })
}

export function registerGalleryFiles(paths) {
  return request({ url: '/admin/gallery/images/register-files', method: 'post', data: { paths } })
}

export function registerGalleryFolder(folderPath, recursive = true) {
  return request({ url: '/admin/gallery/images/register-folder', method: 'post', data: { folder_path: folderPath, recursive } })
}

export function deleteGalleryImage(imageId) {
  return request({ url: `/admin/gallery/images/${imageId}`, method: 'delete' })
}

export function fetchGalleryTaskStatus() {
  return request({ url: '/admin/gallery/status', method: 'get' })
}

export function clearGalleryRecords() {
  return request({ url: '/admin/gallery/clear', method: 'post' })
}

export function browseServerFiles(params) {
  return request({ url: '/admin/file-browser', method: 'get', params })
}

export function openNativeFileDialog(kind) {
  return request({ url: '/admin/native-file-dialog', method: 'post', data: { kind }, timeout: 0 })
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
