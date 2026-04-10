import { ref } from 'vue'
import { applyCurrentModel, fetchModelState } from '@/api/admin'
import { normalizeModelState } from '@/utils/formatters'

function pickSelectionTarget(selectionTarget, nextState, currentSelection) {
  if (selectionTarget === 'preserve' && currentSelection && nextState.availableModels.includes(currentSelection)) {
    return currentSelection
  }

  return nextState.current || ''
}

export function useModelState() {
  const loading = ref(false)
  const applying = ref(false)
  const errorMessage = ref('')
  const modelFiles = ref([])
  const selectedModelFile = ref('')
  const modelState = ref({
    current: '',
    gallery: '',
    device: '未知',
    initialized: false,
    galleryHasRecords: false,
    galleryModelKnown: false,
    galleryMatchesCurrent: true,
    availableModelCount: 0,
    maxResults: 50,
    searchDefaultTopK: 10,
    allowedQuerySuffixes: []
  })

  const loadModelState = async ({ selectionTarget = 'current' } = {}) => {
    loading.value = true
    errorMessage.value = ''

    try {
      const response = await fetchModelState()
      const normalized = normalizeModelState(response.data)

      modelState.value = {
        current: normalized.current,
        gallery: normalized.gallery,
        device: normalized.device,
        initialized: normalized.initialized,
        galleryHasRecords: normalized.galleryHasRecords,
        galleryModelKnown: normalized.galleryModelKnown,
        galleryMatchesCurrent: normalized.galleryMatchesCurrent,
        availableModelCount: normalized.availableModelCount,
        maxResults: normalized.maxResults,
        searchDefaultTopK: normalized.searchDefaultTopK,
        allowedQuerySuffixes: normalized.allowedQuerySuffixes
      }
      modelFiles.value = normalized.availableModels
      selectedModelFile.value = pickSelectionTarget(
        selectionTarget,
        normalized,
        selectedModelFile.value
      )

      return response.data
    } catch (error) {
      errorMessage.value = '模型信息读取失败，请稍后重试。'
      throw error
    } finally {
      loading.value = false
    }
  }

  const applySelectedModel = async () => {
    if (!selectedModelFile.value) {
      return null
    }

    applying.value = true
    errorMessage.value = ''

    try {
      const response = await applyCurrentModel({
        model_file: selectedModelFile.value
      })

      await loadModelState({ selectionTarget: 'current' })
      return response.data
    } catch (error) {
      errorMessage.value = '当前模型切换失败，请稍后重试。'
      throw error
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
    loadModelState,
    applySelectedModel
  }
}
