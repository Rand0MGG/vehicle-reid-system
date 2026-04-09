<template>
  <div class="app-page">
    <div class="app-shell">
      <section class="search-header">
        <div class="search-copy">
          <p class="search-eyebrow">Vehicle ReID Frontend</p>
          <h1>车辆检索前台</h1>
          <p class="search-description">
            上传查询图像后即可开始检索；模型切换和结果数量都集中放在参数区，减少来回查看。
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
        title="模型信息同步失败"
        :message="modelErrorMessage"
      />

      <StatusBanner :tone="feedback.tone" :title="feedback.title" :message="feedback.message" />

      <div class="workspace-grid">
        <QueryUploadPanel
          :file-name="currentFileName"
          :preview-url="previewUrl"
          @file-change="handleFileChange"
          @reset="resetQuery"
        />

        <SectionCard
          eyebrow="Search"
          title="设置检索参数"
          description="当前前台主要使用查询图像、运行模型和返回结果数量这三项信息。"
        >
          <div class="parameter-stats">
            <StatCard
              label="当前模型"
              :value="modelState.current || '未读取到模型'"
              hint="前台当前使用的模型文件"
              mono
            />
            <StatCard
              label="最近耗时"
              :value="searched ? formatDuration(timeCost) : '--'"
              hint="执行一次检索后更新"
            />
          </div>

          <el-form label-position="top" class="parameter-form">
            <el-form-item label="当前运行模型">
              <div class="model-inline-row">
                <el-select
                  v-model="selectedModelFile"
                  filterable
                  placeholder="请选择一个模型文件"
                  :loading="loadingModels"
                  class="model-select"
                >
                  <el-option v-for="item in modelFiles" :key="item" :label="item" :value="item" />
                </el-select>

                <el-button plain :loading="loadingModels" @click="loadCurrentModelMeta">刷新模型</el-button>
                <el-button
                  type="primary"
                  :loading="applyingModel"
                  :disabled="!selectedModelFile || selectedModelFile === modelState.current"
                  @click="handleApplyModel"
                >
                  应用模型
                </el-button>
              </div>
              <p class="field-note">默认模型：{{ modelState.default || '未设置' }}</p>
            </el-form-item>

            <el-form-item label="返回结果数量">
              <el-slider v-model="topK" :min="1" :max="20" show-input />
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
            <p>当前真正可调整的是运行模型和返回结果数量；时间范围筛选暂未启用，只在界面中预留位置。</p>
          </div>

          <ActionBar align="left">
            <el-button type="primary" :loading="loading" @click="handleSearch">
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
import ActionBar from '@/components/base/ActionBar.vue'
import SectionCard from '@/components/base/SectionCard.vue'
import StatCard from '@/components/base/StatCard.vue'
import StatusBanner from '@/components/base/StatusBanner.vue'
import QueryUploadPanel from '@/components/search/QueryUploadPanel.vue'
import ResultGrid from '@/components/search/ResultGrid.vue'
import { useModelMeta } from '@/composables/useModelMeta'
import { useSearchWorkflow } from '@/composables/useSearchWorkflow'
import { useSession } from '@/composables/useSession'
import { formatDuration, getRoleLabel } from '@/utils/formatters'

const router = useRouter()
const { role, isAdmin, syncSession, logoutAndRedirect } = useSession(router)
const {
  loading,
  searched,
  topK,
  dateRange,
  file,
  previewUrl,
  results,
  timeCost,
  feedback,
  handleFileChange,
  resetQuery,
  executeSearch,
  cleanup
} = useSearchWorkflow()
const {
  loading: loadingModels,
  applying: applyingModel,
  errorMessage: modelErrorMessage,
  modelFiles,
  selectedModelFile,
  modelState,
  loadModelMeta,
  applySelectedModel
} = useModelMeta()

const roleLabel = computed(() => getRoleLabel(role.value))
const currentFileName = computed(() => file.value?.name || '')

const loadCurrentModelMeta = async () => {
  try {
    await loadModelMeta({ selectionTarget: 'current' })
  } catch {
    // Inline banner already describes the failure state.
  }
}

const handleApplyModel = async () => {
  if (!selectedModelFile.value) {
    ElMessage.warning('请先选择一个模型文件。')
    return
  }

  try {
    await applySelectedModel()
    ElMessage.success('当前模型已切换。')
  } catch {
    // Error message is handled by the inline banner and axios interceptor.
  }
}

const handleSearch = async () => {
  try {
    const response = await executeSearch()

    if (response) {
      ElMessage.success(`检索完成，共返回 ${response.total_found} 条结果。`)
    }
  } catch {
    // Error state is shown inline.
  }
}

const handleLogout = async () => {
  await logoutAndRedirect()
  ElMessage.success('已退出登录。')
}

onMounted(() => {
  syncSession()
  loadCurrentModelMeta()
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
  align-items: flex-end;
  gap: 12px;
}

.header-meta,
.header-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
  gap: 20px;
  align-items: start;
}

.parameter-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.parameter-form {
  margin-top: 22px;
}

.model-inline-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 10px;
  align-items: center;
}

.model-select {
  width: 100%;
}

.field-note {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.helper-note {
  margin: 6px 0 20px;
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.56);
}

.helper-note strong {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
}

.helper-note p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.55;
}

@media (max-width: 1180px) {
  .search-header {
    grid-template-columns: 1fr;
  }

  .search-side,
  .header-meta,
  .header-actions {
    justify-content: flex-start;
    align-items: flex-start;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .search-header {
    padding: 20px;
    border-radius: 24px;
  }

  .parameter-stats,
  .model-inline-row {
    grid-template-columns: 1fr;
  }
}
</style>
