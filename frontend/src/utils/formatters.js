export function formatDateTime(value) {
  if (!value) {
    return '未知'
  }

  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value.toISOString().replace('T', ' ').slice(0, 19)
  }

  if (typeof value === 'string') {
    return value.replace('T', ' ').slice(0, 19)
  }

  return String(value)
}

export function formatDuration(value) {
  const seconds = Number(value)

  if (!Number.isFinite(seconds)) {
    return '--'
  }

  if (seconds < 1) {
    return `${seconds.toFixed(2)} 秒`
  }

  if (seconds < 10) {
    return `${seconds.toFixed(1)} 秒`
  }

  return `${Math.round(seconds * 10) / 10} 秒`
}

export function normalizeModelState(payload = {}) {
  const currentModel = payload.current_model_file || ''
  const galleryModel = payload.gallery_model_file || ''
  const maxResults = Number(payload.max_results ?? 50)
  const searchDefaultTopK = Number(payload.search_default_top_k ?? 10)
  const allowedQuerySuffixes = Array.isArray(payload.allowed_query_suffixes)
    ? payload.allowed_query_suffixes
    : []

  return {
    current: currentModel,
    gallery: galleryModel,
    device: payload.model_device || '未知',
    initialized: Boolean(payload.initialized),
    galleryHasRecords: Boolean(payload.gallery_has_records),
    galleryModelKnown: Boolean(payload.gallery_model_known ?? galleryModel),
    galleryMatchesCurrent: typeof payload.gallery_model_matches_current === 'boolean'
      ? payload.gallery_model_matches_current
      : !galleryModel || galleryModel === currentModel,
    availableModels: Array.isArray(payload.available_models) ? payload.available_models : [],
    availableModelCount: Number(payload.available_model_count ?? 0),
    maxResults: Number.isFinite(maxResults) ? maxResults : 50,
    searchDefaultTopK: Number.isFinite(searchDefaultTopK) ? searchDefaultTopK : 10,
    allowedQuerySuffixes
  }
}

export const normalizeModelMeta = normalizeModelState

export function normalizeSearchResults(items = []) {
  if (!Array.isArray(items)) {
    return []
  }

  return items.map((item) => ({
    img_url: item?.img_url || '',
    vehicle_id: item?.vehicle_id || '未标注车辆',
    cam_id: item?.cam_id || '未知摄像头',
    capture_time: item?.capture_time || '',
    score: Number.isFinite(Number(item?.score)) ? Number(item.score) : 0
  }))
}

export function getScoreTone(score) {
  if (score >= 0.8) {
    return 'high'
  }

  if (score >= 0.5) {
    return 'mid'
  }

  return 'low'
}

export function getRoleLabel(role) {
  return role === 'admin' ? '管理员' : '普通用户'
}
