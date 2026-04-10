import { onBeforeUnmount, ref } from 'vue'
import { fetchGalleryStatus } from '@/api/admin'

export function useGalleryPolling() {
  const isRunning = ref(false)
  const logs = ref([])
  const errorMessage = ref('')
  let pollTimer = null

  const stopPolling = () => {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  const refreshStatus = async () => {
    errorMessage.value = ''

    try {
      const response = await fetchGalleryStatus()
      isRunning.value = Boolean(response.data?.is_running)
      logs.value = Array.isArray(response.data?.logs) ? response.data.logs : []

      if (!isRunning.value) {
        stopPolling()
      }

      return response.data
    } catch (error) {
      errorMessage.value = '图库状态读取失败，请稍后刷新。'
      stopPolling()
      throw error
    }
  }

  const startPolling = () => {
    if (pollTimer) {
      return
    }

    pollTimer = setInterval(() => {
      refreshStatus().catch(() => {})
    }, 1500)
  }

  onBeforeUnmount(() => {
    stopPolling()
  })

  return {
    isRunning,
    logs,
    errorMessage,
    refreshStatus,
    startPolling,
    stopPolling
  }
}
