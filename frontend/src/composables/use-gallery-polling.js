import { computed, onBeforeUnmount, ref } from 'vue'
import { fetchGalleryTaskStatus } from '@/api/admin'

const defaultStatus = {
  is_running: false,
  logs: [],
  task_id: null,
  model_profile_id: null,
  model_revision_id: null,
  task_type: '',
  total: 0,
  processed: 0,
  created: 0,
  skipped: 0,
  failed: 0,
  message: '',
  started_at: null,
  finished_at: null,
  elapsed_seconds: 0,
  duration_seconds: null,
  progress_percent: 0,
  items_per_second: 0,
  estimated_remaining_seconds: null
}

function normalizeStatus(payload = {}) {
  return {
    ...defaultStatus,
    ...payload,
    is_running: Boolean(payload?.is_running),
    logs: Array.isArray(payload?.logs) ? payload.logs : [],
    total: Number(payload?.total ?? 0),
    processed: Number(payload?.processed ?? 0),
    created: Number(payload?.created ?? 0),
    skipped: Number(payload?.skipped ?? 0),
    failed: Number(payload?.failed ?? 0),
    elapsed_seconds: Number(payload?.elapsed_seconds ?? 0),
    duration_seconds: payload?.duration_seconds === null || payload?.duration_seconds === undefined ? null : Number(payload.duration_seconds),
    progress_percent: Number(payload?.progress_percent ?? 0),
    items_per_second: Number(payload?.items_per_second ?? 0),
    estimated_remaining_seconds: payload?.estimated_remaining_seconds === null || payload?.estimated_remaining_seconds === undefined
      ? null
      : Number(payload.estimated_remaining_seconds)
  }
}

export function useGalleryPolling() {
  const status = ref(normalizeStatus())
  const errorMessage = ref('')
  const pollIntervalMs = ref(1500)
  let pollTimer = null

  const isRunning = computed(() => status.value.is_running)
  const logs = computed(() => status.value.logs)

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
      status.value = normalizeStatus(response.data || {})

      if (!status.value.is_running) {
        stopPolling()
      }

      return status.value
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
    status,
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
