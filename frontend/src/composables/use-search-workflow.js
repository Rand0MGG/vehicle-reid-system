import { ref } from 'vue'
import { searchVehicle } from '@/api/search'
import { normalizeSearchResults } from '@/utils/formatters'

function describeSupportedFormats(allowedQuerySuffixes) {
  if (!Array.isArray(allowedQuerySuffixes) || allowedQuerySuffixes.length === 0) {
    return '支持 JPG、PNG 等常见图片格式，上传后即可开始检索。'
  }

  return `当前支持这些图片格式：${allowedQuerySuffixes.join(', ')}。`
}

export function useSearchWorkflow() {
  const loading = ref(false)
  const searched = ref(false)
  const topK = ref(10)
  const maxResults = ref(50)
  const allowedQuerySuffixes = ref([])
  const selectedModelId = ref(0)
  const searchMode = ref('fast')
  const deepThinking = ref(false)
  const searchMeta = ref({
    searchMode: 'fast',
    featureDim: 0,
    gallerySize: 0,
    rerankCandidateCount: 0,
    deepThinkingRequested: false,
    deepThinkingUsed: false
  })
  const dateRange = ref([])
  const file = ref(null)
  const previewUrl = ref('')
  const results = ref([])
  const timeCost = ref(0)
  const feedback = ref({
    tone: 'neutral',
    title: '等待上传查询图像',
    message: '支持 JPG、PNG 等常见图片格式，上传后即可开始检索。'
  })

  const setFeedback = (tone, title, message) => {
    feedback.value = { tone, title, message }
  }

  const revokePreview = () => {
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = ''
    }
  }

  const resetResults = () => {
    results.value = []
    timeCost.value = 0
    searched.value = false
    searchMeta.value = {
      searchMode: searchMode.value,
      featureDim: 0,
      gallerySize: 0,
      rerankCandidateCount: 0,
      deepThinkingRequested: deepThinking.value,
      deepThinkingUsed: false
    }
  }

  const handleFileChange = (uploadFile) => {
    if (!uploadFile?.raw) {
      return
    }

    revokePreview()
    file.value = uploadFile.raw
    previewUrl.value = URL.createObjectURL(uploadFile.raw)
    resetResults()
    setFeedback('success', '查询图像已准备好', `当前文件：${file.value.name}`)
  }

  const resetQuery = () => {
    revokePreview()
    file.value = null
    resetResults()
    setFeedback('neutral', '等待上传查询图像', describeSupportedFormats(allowedQuerySuffixes.value))
  }

  const applyRuntimeDefaults = ({ defaultTopK, maxResultLimit, allowedSuffixes, selectedModel, supportsPro, supportsDeepThinking } = {}) => {
    const normalizedMax = Number(maxResultLimit)
    if (Number.isFinite(normalizedMax)) {
      maxResults.value = Math.max(1, Math.round(normalizedMax))
    }

    if (Array.isArray(allowedSuffixes)) {
      allowedQuerySuffixes.value = allowedSuffixes
    }

    const normalizedTopK = Number(defaultTopK)
    if (Number.isFinite(normalizedTopK)) {
      topK.value = Math.min(maxResults.value, Math.max(1, Math.round(normalizedTopK)))
    } else {
      topK.value = Math.min(topK.value, maxResults.value)
    }

    if (!file.value) {
      setFeedback('neutral', '等待上传查询图像', describeSupportedFormats(allowedQuerySuffixes.value))
    }

    if (selectedModel?.id) {
      selectedModelId.value = Number(selectedModel.id)
    }

    if (!supportsPro && searchMode.value === 'pro') {
      searchMode.value = 'fast'
    }
    if (!supportsDeepThinking) {
      deepThinking.value = false
    }
  }

  const executeSearch = async () => {
    if (!file.value) {
      setFeedback('warning', '请先上传查询图像', '上传一张车辆图片后才能开始检索。')
      return null
    }
    if (!selectedModelId.value) {
      setFeedback('warning', '请先选择模型', '请选择一个管理员发布的模型后再检索。')
      return null
    }

    loading.value = true
    setFeedback('info', '正在检索图库', '系统正在提取特征并计算相似度，请稍候。')

    try {
      const formData = new FormData()
      formData.append('file', file.value)
      formData.append('top_k', String(topK.value))
      formData.append('model_profile_id', String(selectedModelId.value))
      formData.append('search_mode', searchMode.value)
      formData.append('deep_thinking', deepThinking.value ? 'true' : 'false')

      const response = await searchVehicle(formData, { deepThinking: deepThinking.value })
      const normalizedResults = normalizeSearchResults(response.data?.results)

      results.value = normalizedResults
      timeCost.value = Number(response.data?.time_cost) || 0
      searchMeta.value = {
        searchMode: response.data?.search_mode || searchMode.value,
        featureDim: Number(response.data?.feature_dim ?? 0),
        gallerySize: Number(response.data?.gallery_size ?? 0),
        rerankCandidateCount: Number(response.data?.rerank_candidate_count ?? 0),
        deepThinkingRequested: Boolean(response.data?.deep_thinking_requested),
        deepThinkingUsed: Boolean(response.data?.deep_thinking_used)
      }
      searched.value = true

      if (normalizedResults.length > 0) {
        setFeedback(
          'success',
          '检索已完成',
          response.data?.deep_thinking_used
            ? `共返回 ${response.data?.total_found ?? normalizedResults.length} 条结果，深度思考重排了 ${response.data?.rerank_candidate_count ?? 0} 个候选。`
            : `共返回 ${response.data?.total_found ?? normalizedResults.length} 条结果。`
        )
      } else {
        setFeedback('warning', '没有找到匹配结果', '可以尝试更换更清晰的查询图像，或者适当提高返回结果数量。')
      }

      return response.data
    } catch (error) {
      results.value = []
      timeCost.value = 0
      searched.value = true
      const isTimeout = /timeout|exceeded/i.test(error?.message || '')
      setFeedback(
        'danger',
        isTimeout ? '检索超时' : '检索失败',
        isTimeout ? '深度思考计算时间过长，请减少返回数量或调低候选上限后再试。' : '请求没有成功完成，请确认后端服务、模型和图库状态。'
      )
      throw error
    } finally {
      loading.value = false
    }
  }

  const cleanup = () => {
    revokePreview()
  }

  return {
    loading,
    searched,
    topK,
    maxResults,
    allowedQuerySuffixes,
    selectedModelId,
    searchMode,
    deepThinking,
    searchMeta,
    dateRange,
    file,
    previewUrl,
    results,
    timeCost,
    feedback,
    handleFileChange,
    resetQuery,
    applyRuntimeDefaults,
    executeSearch,
    cleanup
  }
}
