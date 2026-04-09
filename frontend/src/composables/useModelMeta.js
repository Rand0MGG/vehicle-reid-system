import { ref } from 'vue'
import { fetchModelFiles, selectModelFile } from '@/api/admin'
import { normalizeModelMeta } from '@/utils/formatters'

function getSelectionTarget(selectionTarget, modelState, currentSelection) {
  if (selectionTarget === 'default') {
    return modelState.default || modelState.current || ''
  }

  if (selectionTarget === 'preserve' && currentSelection) {
    return currentSelection
  }

  return modelState.current || modelState.default || ''
}

export function useModelMeta() {
  const loading = ref(false)
  const applying = ref(false)
  const errorMessage = ref('')
  const modelFiles = ref([])
  const selectedModelFile = ref('')
  const modelState = ref({
    current: '',
    default: '',
    device: '未知',
    initialized: false
  })

  const loadModelMeta = async ({ selectionTarget = 'current' } = {}) => {
    loading.value = true
    errorMessage.value = ''

    try {
      const response = await fetchModelFiles()
      const normalized = normalizeModelMeta(response.data)

      modelState.value = {
        current: normalized.current,
        default: normalized.default,
        device: normalized.device,
        initialized: normalized.initialized
      }
      modelFiles.value = normalized.availableModels
      selectedModelFile.value = getSelectionTarget(
        selectionTarget,
        modelState.value,
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

  const applySelectedModel = async ({ setAsDefault = false } = {}) => {
    if (!selectedModelFile.value) {
      return null
    }

    applying.value = true
    errorMessage.value = ''

    try {
      const response = await selectModelFile({
        model_file: selectedModelFile.value,
        set_as_default: setAsDefault
      })

      await loadModelMeta({ selectionTarget: setAsDefault ? 'default' : 'current' })
      return response.data
    } catch (error) {
      errorMessage.value = setAsDefault
        ? '默认模型保存失败，请稍后重试。'
        : '当前模型切换失败，请稍后重试。'
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
    loadModelMeta,
    applySelectedModel
  }
}
