import request from '@/utils/request'

export function fetchAuditLogs(page = 1, size = 15) {
  return request({
    url: '/admin/logs',
    method: 'get',
    params: { page, size }
  })
}

export function syncGalleryData() {
  return request({
    url: '/admin/gallery/sync',
    method: 'post'
  })
}

export function fetchUserList() {
  return request({
    url: '/admin/users',
    method: 'get'
  })
}

export function createNewUser(data) {
  return request({
    url: '/admin/users',
    method: 'post',
    data
  })
}

export function removeUser(userId) {
  return request({
    url: `/admin/users/${userId}`,
    method: 'delete'
  })
}