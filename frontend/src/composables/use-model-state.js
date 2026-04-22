import { ref } from 'vue'
import { fetchModelState } from '@/api/admin'
import { normalizeModelState } from '@/utils/formatters'

export function useModelState() {
  const loading = ref(false)
  const applying = ref(false)
  const errorMessage = ref('')
  const modelFiles = ref([])
  const configFiles = ref([])
  const modelProfiles = ref([])
  const selectedProfileId = ref(0)
  const modelState = ref(normalizeModelState({}))

  const loadModelState = async () => {
    loading.value = true
    errorMessage.value = ''
    try {
      const response = await fetchModelState()
      const normalized = normalizeModelState(response.data)
      modelState.value = normalized
      modelFiles.value = normalized.availableModels
      configFiles.value = normalized.availableConfigs
      modelProfiles.value = normalized.modelProfiles
      selectedProfileId.value = normalized.publicModelProfiles[0]?.id || normalized.modelProfiles[0]?.id || 0
      return response.data
    } catch (error) {
      errorMessage.value = '模型信息读取失败，请稍后重试。'
      throw error
    } finally {
      loading.value = false
    }
  }

  const applySelectedModel = async () => null

  return {
    loading,
    applying,
    errorMessage,
    modelFiles,
    configFiles,
    modelProfiles,
    selectedProfileId,
    selectedModelFile: selectedProfileId,
    modelState,
    loadModelState,
    applySelectedModel
  }
}
