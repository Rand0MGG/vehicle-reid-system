<template>
  <div class="app-page">
    <div class="app-shell">
      <section class="search-header">
        <div class="search-copy">
          <p class="search-eyebrow">Vehicle ReID Frontend</p>
          <h1>车辆检索前台</h1>
          <p class="search-description">
            选择管理员发布的模型，上传查询图像后即可开始检索。Fast 使用全局特征，Pro 使用完整 concat 特征。
          </p>
        </div>

        <div class="search-side">
          <div class="header-meta">
            <span class="app-chip">当前身份 <strong>{{ roleLabel }}</strong></span>
            <span class="app-chip">可用模型 <strong>{{ publicModels.length }}</strong></span>
          </div>

          <div class="header-actions">
            <el-button v-if="isAdmin" plain @click="router.push('/admin')">进入后台</el-button>
            <el-button @click="handleLogout">退出登录</el-button>
          </div>
        </div>
      </section>

      <StatusBanner v-if="modelError" tone="danger" title="模型列表读取失败" :message="modelError" />
      <StatusBanner :tone="feedback.tone" :title="feedback.title" :message="feedback.message" />

      <div class="workspace-grid">
        <QueryUploadPanel
          :file-name="currentFileName"
          :preview-url="previewUrl"
          :accept="queryAccept"
          :helper-message="uploadHelperMessage"
          @file-change="handleFileChange"
          @reset="resetQuery"
        />

        <SectionCard
          eyebrow="Search"
          title="设置检索参数"
          description="模型、特征视图和深度思考都在本次查询中明确提交。"
        >
          <el-form label-position="top" class="parameter-form">
            <el-form-item label="选择模型">
              <el-select v-model="selectedModelId" placeholder="请选择模型" filterable @change="handleModelChange">
                <el-option
                  v-for="model in publicModels"
                  :key="model.id"
                  :label="`${model.name} · ${model.full_feature_dim || '--'} 维`"
                  :value="model.id"
                />
              </el-select>
            </el-form-item>
          </el-form>

          <div class="parameter-stats">
            <StatCard label="当前模型" :value="selectedModel?.name || '未选择模型'" :hint="selectedModel?.description || '请选择模型'" text />
            <StatCard
              label="特征视图"
              :value="searchMode === 'pro' ? `${selectedModel?.full_feature_dim || 0} 维` : `${selectedModel?.global_feature_dim || 0} 维`"
              :hint="searchMode === 'pro' ? 'Pro 使用完整 concat 特征' : 'Fast 截取完整向量的 global 部分'"
              number
            />
            <StatCard label="最近耗时" :value="searched ? formatDuration(timeCost) : '--'" hint="完成一次检索后更新" number />
          </div>

          <el-form label-position="top" class="parameter-form">
            <el-form-item label="检索模式">
              <el-radio-group v-model="searchMode" class="mode-segment">
                <el-radio-button label="fast">Fast</el-radio-button>
                <el-tooltip :disabled="!proDisabled" content="当前模型不支持 Pro 检索" placement="top">
                  <span>
                    <el-radio-button label="pro" :disabled="proDisabled">Pro</el-radio-button>
                  </span>
                </el-tooltip>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="深度思考">
              <div class="deep-thinking-row">
                <el-tooltip :disabled="!deepThinkingDisabled" :content="deepThinkingDisabledReason" placement="top">
                  <span>
                    <el-switch
                      v-model="deepThinking"
                      :disabled="deepThinkingDisabled"
                      active-text="开启"
                      inactive-text="关闭"
                    />
                  </span>
                </el-tooltip>
                <p>开启后只在当前特征矩阵上重新排序，不重新读取图片，也不重写数据库。</p>
              </div>
            </el-form-item>

            <el-form-item label="返回结果数量">
              <el-slider v-model="topK" :min="1" :max="maxResults" show-input />
            </el-form-item>

            <el-form-item label="时间范围过滤">
              <el-date-picker
                v-model="dateRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                disabled
              />
            </el-form-item>
          </el-form>

          <div class="helper-note">
            <strong>{{ searched ? '本次检索' : '当前可用能力' }}</strong>
            <p>
              {{ searched
                ? `模式 ${searchMeta.searchMode.toUpperCase()}，特征 ${searchMeta.featureDim || '--'} 维，深度思考${searchMeta.deepThinkingUsed ? '已启用' : '未启用'}。`
                : capabilityText }}
            </p>
          </div>

          <ActionBar align="left">
            <el-button type="primary" :loading="loading" :disabled="searchDisabled" @click="handleSearch">
              {{ loading ? '正在执行检索...' : '开始检索' }}
            </el-button>
            <el-button plain :disabled="!currentFileName" @click="resetQuery">重置当前查询</el-button>
          </ActionBar>
        </SectionCard>
      </div>

      <ResultGrid :results="results" :searched="searched" :loading="loading" :time-cost="timeCost" />
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ActionBar from '@/components/base/action-bar.vue'
import SectionCard from '@/components/base/section-card.vue'
import StatCard from '@/components/base/stat-card.vue'
import StatusBanner from '@/components/base/status-banner.vue'
import QueryUploadPanel from '@/components/search/query-upload-panel.vue'
import ResultGrid from '@/components/search/result-grid.vue'
import { fetchPublicModels } from '@/api/search'
import { useSearchWorkflow } from '@/composables/use-search-workflow'
import { useSession } from '@/composables/use-session'
import { formatDuration, getRoleLabel, normalizeProfile } from '@/utils/formatters'

const router = useRouter()
const { role, isAdmin, syncSession, logoutAndRedirect } = useSession(router)
const publicModels = ref([])
const modelError = ref('')
const {
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
} = useSearchWorkflow()

const roleLabel = computed(() => getRoleLabel(role.value))
const currentFileName = computed(() => file.value?.name || '')
const selectedModel = computed(() => publicModels.value.find((item) => Number(item.id) === Number(selectedModelId.value)) || null)
const proDisabled = computed(() => !selectedModel.value?.supports_concat)
const deepThinkingDisabled = computed(() => !selectedModel.value?.supports_rerank)
const deepThinkingDisabledReason = computed(() => (
  selectedModel.value?.supports_rerank ? '当前图库规模超过深度思考上限' : '当前模型不支持深度思考'
))
const searchDisabled = computed(() => loading.value || !selectedModel.value)
const capabilityText = computed(() => {
  if (!selectedModel.value) {
    return '请选择一个管理员发布的模型。'
  }
  return `Fast 使用 ${selectedModel.value.global_feature_dim} 维，Pro 使用 ${selectedModel.value.full_feature_dim} 维。`
})
const queryAccept = computed(() => allowedQuerySuffixes.value.length ? allowedQuerySuffixes.value.join(',') : 'image/*')
const uploadHelperMessage = computed(() => {
  if (!allowedQuerySuffixes.value.length) {
    return '建议上传主体清晰、角度稳定的车辆图像。'
  }
  return `建议上传主体清晰、角度稳定的车辆图像。当前支持：${allowedQuerySuffixes.value.join(', ')}`
})

const applySelectedModelDefaults = () => {
  const model = selectedModel.value
  applyRuntimeDefaults({
    selectedModel: model,
    supportsPro: Boolean(model?.supports_concat),
    supportsDeepThinking: Boolean(model?.supports_rerank)
  })
}

const handleModelChange = () => {
  applySelectedModelDefaults()
}

const loadPublicModels = async () => {
  modelError.value = ''
  try {
    const response = await fetchPublicModels()
    publicModels.value = Array.isArray(response.data?.items)
      ? response.data.items.map(normalizeProfile)
      : []
    applyRuntimeDefaults({
      defaultTopK: response.data?.search_default_top_k,
      maxResultLimit: response.data?.max_results,
      allowedSuffixes: response.data?.allowed_query_suffixes
    })
    if (!selectedModelId.value && publicModels.value.length) {
      selectedModelId.value = Number(publicModels.value[0].id)
    }
    applySelectedModelDefaults()
  } catch {
    modelError.value = '请确认后端服务可用，并且管理员已经发布至少一个模型。'
  }
}

const handleSearch = async () => {
  try {
    const response = await executeSearch()
    if (response) {
      ElMessage.success(`检索完成，共返回 ${response.total_found} 条结果。`)
    }
  } catch {
    // The request layer and inline status banner provide the error message.
  }
}

const handleLogout = async () => {
  await logoutAndRedirect()
  ElMessage.success('已退出登录。')
}

onMounted(() => {
  syncSession()
  loadPublicModels()
})

onBeforeUnmount(() => {
  cleanup()
})
</script>

<style scoped>
.search-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20px;
  padding: 24px 28px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: var(--surface-panel);
  box-shadow: var(--shadow-whisper);
}

.search-copy h1 {
  margin: 10px 0 0;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: clamp(30px, 4vw, 48px);
  font-weight: 500;
  line-height: 1.08;
}

.search-eyebrow {
  margin: 0;
  color: var(--text-accent);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.search-description {
  max-width: 760px;
  margin: 14px 0 0;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.6;
}

.search-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-end;
}

.header-meta,
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: flex-end;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
  gap: 20px;
  align-items: stretch;
}

.parameter-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 8px 0 18px;
}

.mode-segment {
  padding: 4px;
  border: 1px solid rgba(171, 96, 67, 0.24);
  border-radius: 8px;
  background: rgba(255, 250, 244, 0.78);
  box-shadow: 0 0 0 4px rgba(171, 96, 67, 0.08);
}

.mode-segment :deep(.el-radio-button__inner) {
  border-radius: 6px;
  border: 0;
  font-weight: 700;
}

.mode-segment :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #a75f42;
  border-color: #a75f42;
  box-shadow: none;
}

.deep-thinking-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.deep-thinking-row p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.helper-note {
  margin: 18px 0 20px;
  padding: 16px 18px;
  border: 1px solid rgba(171, 96, 67, 0.2);
  border-radius: 8px;
  background: rgba(255, 250, 244, 0.68);
  box-shadow: 0 12px 28px rgba(91, 55, 38, 0.08);
}

.helper-note strong {
  display: block;
  color: var(--text-primary);
  font-size: 15px;
}

.helper-note p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.55;
}

@media (max-width: 1080px) {
  .workspace-grid,
  .parameter-stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .search-header {
    grid-template-columns: 1fr;
    padding: 22px;
  }

  .search-side,
  .header-meta,
  .header-actions {
    align-items: flex-start;
    justify-content: flex-start;
  }
}
</style>
