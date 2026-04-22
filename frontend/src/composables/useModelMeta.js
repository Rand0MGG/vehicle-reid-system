import { ref } from 'vue'
import { fetchModelState } from '@/api/admin'
import { normalizeModelMeta } from '@/utils/formatters'

function pickSelectionTarget(selectionTarget, nextState, currentSelection) {
  const candidates = nextState.publicModelProfiles.length
    ? nextState.publicModelProfiles
    : nextState.availableModelProfiles

  if (selectionTarget === 'preserve' && currentSelection) {
    const preserved = candidates.find((item) => Number(item.id) === Number(currentSelection))
    if (preserved) {
      return preserved.id
    }
  }

  return candidates[0]?.id || 0
}

export function useModelMeta() {
  const loading = ref(false)
  const applying = ref(false)
  const errorMessage = ref('')
  const modelFiles = ref([])
  const selectedModelFile = ref(0)
  const modelState = ref({
    current: '',
    gallery: '',
    device: '未知',
    initialized: false,
    galleryMatchesCurrent: true
  })

  const loadModelMeta = async ({ selectionTarget = 'current' } = {}) => {
    loading.value = true
    errorMessage.value = ''

    try {
      const response = await fetchModelState()
      const normalized = normalizeModelMeta(response.data)
      const profiles = normalized.publicModelProfiles.length
        ? normalized.publicModelProfiles
        : normalized.availableModelProfiles
      const selectedProfile = profiles.find((item) => Number(item.id) === Number(selectedModelFile.value)) || profiles[0]

      modelState.value = {
        current: selectedProfile?.name || '',
        gallery: selectedProfile?.feature_status?.is_complete ? selectedProfile?.name || '' : '',
        device: normalized.device,
        initialized: normalized.initialized,
        galleryMatchesCurrent: true
      }
      modelFiles.value = profiles.map((item) => ({ label: item.name, value: item.id }))
      selectedModelFile.value = pickSelectionTarget(selectionTarget, normalized, selectedModelFile.value)

      return response.data
    } catch (error) {
      errorMessage.value = '模型信息读取失败，请稍后重试。'
      throw error
    } finally {
      loading.value = false
    }
  }

  const applySelectedModel = async () => {
    applying.value = true
    try {
      return null
    } finally {
      applying.value = false
    }
  }

  return {
    loading,
    applying,
    errorMessage,
    modelFiles,
    selectedModelFile,
    modelState,
    loadModelMeta,
    applySelectedModel
  }
}
