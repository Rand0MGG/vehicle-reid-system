import { onBeforeUnmount, ref } from 'vue'
import { fetchGalleryTaskStatus } from '@/api/admin'

export function useGalleryPolling() {
  const isRunning = ref(false)
  const logs = ref([])
  const errorMessage = ref('')
  const pollIntervalMs = ref(1500)
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
      const response = await fetchGalleryTaskStatus()
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
    stopPolling()

    pollTimer = setInterval(() => {
      refreshStatus().catch(() => {})
    }, pollIntervalMs.value)
  }

  const setPollInterval = (nextIntervalMs) => {
    const normalized = Number(nextIntervalMs)
    if (!Number.isFinite(normalized)) {
      return
    }

    pollIntervalMs.value = Math.max(500, Math.round(normalized))

    if (pollTimer) {
      startPolling()
    }
  }

  onBeforeUnmount(() => {
    stopPolling()
  })

  return {
    isRunning,
    logs,
    errorMessage,
    pollIntervalMs,
    refreshStatus,
    startPolling,
    stopPolling,
    setPollInterval
  }
}
