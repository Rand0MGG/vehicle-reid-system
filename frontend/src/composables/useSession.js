import { computed, ref } from 'vue'
import { logout } from '@/api/auth'

export function useSession(router) {
  const token = ref('')
  const role = ref('')

  const syncSession = () => {
    token.value = localStorage.getItem('access_token') || ''
    role.value = localStorage.getItem('user_role') || ''
  }

  const persistSession = ({ accessToken, role: nextRole }) => {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('user_role', nextRole)
    syncSession()
  }

  const clearSession = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    syncSession()
  }

  const logoutAndRedirect = async () => {
    try {
      if (token.value) {
        await logout()
      }
    } catch {
      // Ignore logout API failures and always clear the local session.
    } finally {
      clearSession()
      if (router) {
        await router.push('/login')
      }
    }
  }

  syncSession()

  return {
    token,
    role,
    isAuthenticated: computed(() => Boolean(token.value)),
    isAdmin: computed(() => role.value === 'admin'),
    syncSession,
    persistSession,
    clearSession,
    logoutAndRedirect
  }
}
