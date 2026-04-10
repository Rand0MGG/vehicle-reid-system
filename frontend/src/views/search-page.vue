<template>
  <div class="app-page">
    <div class="app-shell">
      <section class="search-header">
        <div class="search-copy">
          <p class="search-eyebrow">Vehicle ReID Frontend</p>
          <h1>车辆检索前台</h1>
          <p class="search-description">
            上传查询图像后即可开始检索。模型切换由管理员统一处理，前台只保留必要的检索参数与结果展示。
          </p>
        </div>

        <div class="search-side">
          <div class="header-meta">
            <span class="app-chip">当前身份 <strong>{{ roleLabel }}</strong></span>
            <span class="app-chip">运行设备 <strong>{{ modelState.device || '未知' }}</strong></span>
          </div>

          <div class="header-actions">
            <el-button v-if="isAdmin" plain @click="router.push('/admin')">进入后台</el-button>
            <el-button @click="handleLogout">退出登录</el-button>
          </div>
        </div>
      </section>

      <StatusBanner
        v-if="modelErrorMessage"
        tone="danger"
        title="模型信息读取失败"
        :message="modelErrorMessage"
      />

      <StatusBanner
        v-if="searchBlocked"
        tone="warning"
        :title="searchBlockedTitle"
        :message="searchBlockedMessage"
      />

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
          description="当前前台只开放返回结果数量设置，模型由管理员统一维护。"
        >
          <div class="parameter-stats">
            <StatCard
              label="当前模型"
              :value="modelState.current || '尚未读取到模型'"
              hint="当前检索正在使用的模型文件"
              mono
            />
            <StatCard
              label="图库特征模型"
              :value="modelState.gallery || '尚未记录'"
              hint="当前图库中的特征数据由这个模型计算得到"
              mono
            />
            <StatCard
              label="最近耗时"
              :value="searched ? formatDuration(timeCost) : '--'"
              hint="完成一次检索后更新"
            />
          </div>

          <el-form label-position="top" class="parameter-form">
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
            <strong>当前可调整内容</strong>
            <p>当前前台只允许调整返回结果数量。可上传格式由后台统一配置，时间范围过滤暂未启用。</p>
          </div>

          <ActionBar align="left">
            <el-button type="primary" :loading="loading" :disabled="searchBlocked" @click="handleSearch">
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
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ActionBar from '@/components/base/action-bar.vue'
import SectionCard from '@/components/base/section-card.vue'
import StatCard from '@/components/base/stat-card.vue'
import StatusBanner from '@/components/base/status-banner.vue'
import QueryUploadPanel from '@/components/search/query-upload-panel.vue'
import ResultGrid from '@/components/search/result-grid.vue'
import { useModelState } from '@/composables/use-model-state'
import { useSearchWorkflow } from '@/composables/use-search-workflow'
import { useSession } from '@/composables/use-session'
import { formatDuration, getRoleLabel } from '@/utils/formatters'

const router = useRouter()
const { role, isAdmin, syncSession, logoutAndRedirect } = useSession(router)
const {
  loading,
  searched,
  topK,
  maxResults,
  allowedQuerySuffixes,
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
const {
  errorMessage: modelErrorMessage,
  modelState,
  loadModelState
} = useModelState()

const roleLabel = computed(() => getRoleLabel(role.value))
const currentFileName = computed(() => file.value?.name || '')
const galleryModelUnknown = computed(
  () => modelState.value.galleryHasRecords && !modelState.value.galleryModelKnown
)
const galleryModelMismatch = computed(
  () => modelState.value.galleryModelKnown && !modelState.value.galleryMatchesCurrent
)
const searchBlocked = computed(() => galleryModelUnknown.value || galleryModelMismatch.value)
const searchBlockedTitle = computed(() => (
  galleryModelUnknown.value ? '图库特征模型尚未记录' : '当前模型与图库特征模型不一致'
))
const searchBlockedMessage = computed(() => {
  if (galleryModelUnknown.value) {
    return '当前图库已有特征数据，但没有记录它使用的模型。请联系管理员重新处理全部图片后再检索。'
  }

  return '当前检索已暂时停用，请联系管理员在后台重新处理全部图片后再继续检索。'
})
const queryAccept = computed(() => {
  if (!allowedQuerySuffixes.value.length) {
    return 'image/*'
  }

  return allowedQuerySuffixes.value.join(',')
})
const uploadHelperMessage = computed(() => {
  if (!allowedQuerySuffixes.value.length) {
    return '建议上传主体清晰、角度稳定的车辆图像。'
  }

  return `建议上传主体清晰、角度稳定的车辆图像。当前支持：${allowedQuerySuffixes.value.join(', ')}`
})

const loadSearchContext = async () => {
  try {
    await loadModelState()
    applyRuntimeDefaults({
      defaultTopK: modelState.value.searchDefaultTopK,
      maxResultLimit: modelState.value.maxResults,
      allowedSuffixes: modelState.value.allowedQuerySuffixes
    })
  } catch {
    // Inline banner already describes the failure state.
  }
}

const handleSearch = async () => {
  try {
    const response = await executeSearch()

    if (response) {
      ElMessage.success(`检索完成，共返回 ${response.total_found} 条结果。`)
    }
  } catch {
    // Error state is shown inline and by the request layer.
  }
}

const handleLogout = async () => {
  await logoutAndRedirect()
  ElMessage.success('已退出登录。')
}

onMounted(() => {
  syncSession()
  loadSearchContext()
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
  border-radius: 28px;
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
  grid-template-columns: minmax(0, 1.25fr) minmax(340px, 0.9fr);
  gap: 20px;
  align-items: stretch;
}

.parameter-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.parameter-form :deep(.el-form-item) + :deep(.el-form-item) {
  margin-top: 8px;
}

.helper-note {
  margin: 18px 0 20px;
  padding: 16px 18px;
  border: 1px solid var(--border-soft);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.48);
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
