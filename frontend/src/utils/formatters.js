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

export function normalizeProfile(profile = {}) {
  const revision = profile.active_revision || {}
  return {
    id: Number(profile.id || 0),
    name: profile.name || '未命名模型',
    description: profile.description || '',
    is_enabled: Boolean(profile.is_enabled ?? profile.is_active),
    is_active: Boolean(profile.is_enabled ?? profile.is_active),
    is_public: Boolean(profile.is_public),
    display_order: Number(profile.display_order ?? 0),
    active_revision_id: Number(profile.active_revision_id || revision.id || 0),
    weights_file: profile.weights_file || revision.weights_file || '',
    config_file: profile.config_file || revision.config_file || '',
    supports_concat: Boolean(profile.supports_concat ?? revision.supports_concat),
    supports_rerank: Boolean(profile.supports_rerank ?? revision.supports_rerank),
    global_feature_dim: Number(profile.global_feature_dim ?? revision.global_feature_dim ?? 0),
    full_feature_dim: Number(profile.full_feature_dim ?? revision.full_feature_dim ?? 0),
    fast_inference_mode: profile.fast_inference_mode || revision.fast_inference_mode || 'global',
    pro_inference_mode: profile.pro_inference_mode || revision.pro_inference_mode || 'global_detail',
    model_signature: profile.model_signature || revision.signature || '',
    active_revision: revision,
    feature_status: profile.feature_status || {
      image_count: 0,
      feature_count: 0,
      missing_count: 0,
      is_complete: false
    },
    revisions: Array.isArray(profile.revisions) ? profile.revisions : []
  }
}

export function normalizeModelState(payload = {}) {
  const modelProfiles = Array.isArray(payload.model_profiles)
    ? payload.model_profiles.map(normalizeProfile)
    : []
  const publicProfiles = Array.isArray(payload.public_model_profiles)
    ? payload.public_model_profiles.map(normalizeProfile)
    : modelProfiles.filter((item) => item.is_enabled && item.is_public)
  const maxResults = Number(payload.max_results ?? 50)
  const searchDefaultTopK = Number(payload.search_default_top_k ?? 10)
  const maxDeepThinkingGallerySize = Number(payload.max_deep_thinking_gallery_size ?? 5000)

  return {
    modelProfiles,
    availableModelProfiles: Array.isArray(payload.available_model_profiles)
      ? payload.available_model_profiles.map(normalizeProfile)
      : modelProfiles.filter((item) => item.is_enabled),
    publicModelProfiles: publicProfiles,
    availableModels: Array.isArray(payload.available_models) ? payload.available_models : [],
    availableConfigs: Array.isArray(payload.available_configs) ? payload.available_configs : [],
    device: payload.model_device || '未知',
    initialized: Boolean(payload.initialized),
    galleryImageCount: Number(payload.gallery_image_count ?? 0),
    galleryFeatureCount: Number(payload.gallery_feature_count ?? 0),
    maxDeepThinkingGallerySize: Number.isFinite(maxDeepThinkingGallerySize) ? maxDeepThinkingGallerySize : 5000,
    maxResults: Number.isFinite(maxResults) ? maxResults : 50,
    searchDefaultTopK: Number.isFinite(searchDefaultTopK) ? searchDefaultTopK : 10,
    allowedQuerySuffixes: Array.isArray(payload.allowed_query_suffixes) ? payload.allowed_query_suffixes : []
  }
}

export const normalizeModelMeta = normalizeModelState

export function normalizeSearchResults(items = []) {
  if (!Array.isArray(items)) {
    return []
  }

  return items.map((item) => ({
    image_id: Number(item?.image_id ?? 0),
    img_url: item?.img_url || '',
    vehicle_id: item?.vehicle_id || '未标注车辆',
    cam_id: item?.cam_id || '未知摄像头',
    capture_time: item?.capture_time || '',
    score: Number.isFinite(Number(item?.score)) ? Number(item.score) : 0,
    rerank_distance: Number.isFinite(Number(item?.rerank_distance)) ? Number(item.rerank_distance) : null
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
