import request from '@/utils/request'

export function login(username, password) {
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)
  
  return request({
    url: '/auth/login',
    method: 'post',
    data: params
  })
}