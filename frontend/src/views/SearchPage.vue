<template>
  <div class="search-page">
    <header class="topbar">
      <div class="brand-block">
        <div class="brand-mark">V</div>
        <div>
          <p class="brand-kicker">Vehicle ReID Frontend</p>
          <h1>车辆检索前台</h1>
        </div>
      </div>

      <div class="topbar-actions">
        <div class="meta-pill">
          <span class="meta-label">当前模型</span>
          <span class="meta-value model-value" :title="currentModelLabel">{{ currentModelLabel }}</span>
        </div>
        <div class="meta-pill">
          <span class="meta-label">身份</span>
          <span class="meta-value">{{ isAdmin ? '管理员' : '普通用户' }}</span>
        </div>
        <el-button v-if="isAdmin" plain @click="goToAdmin">进入后台</el-button>
        <el-button @click="handleLogout">退出登录</el-button>
      </div>
    </header>

    <section class="hero-panel">
      <div class="hero-copy">
        <span class="section-kicker">Search Workspace</span>
        <h2>上传一张车辆图像，快速检索图库中的相似目标。</h2>
        <p>
          前台保留原有的图片上传、Top-K 检索、结果预览和登出功能，同时加入当前模型展示、
          更清晰的状态反馈以及管理员的后台入口。
        </p>
      </div>

      <div class="hero-stats">
        <article class="stat-card">
          <span>最近一次检索耗时</span>
          <strong>{{ searched ? `${timeCost}s` : '未执行' }}</strong>
        </article>
        <article class="stat-card">
          <span>结果数量</span>
          <strong>{{ searched ? results.length : '--' }}</strong>
        </article>
        <article class="stat-card">
          <span>最高相似度</span>
          <strong>{{ bestScoreLabel }}</strong>
        </article>
      </div>
    </section>

    <section class="workspace-grid">
      <article class="query-card">
        <div class="card-heading">
          <span class="section-kicker">Query</span>
          <h3>查询图像</h3>
          <p>支持拖拽上传。更换图片后会自动清空上一轮检索结果。</p>
        </div>

        <el-upload
          class="query-upload"
          drag
          action="#"
          accept="image/*"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleFileChange"
        >
          <div v-if="previewUrl" class="preview-box">
            <img :src="previewUrl" alt="query preview" class="preview-image" />
            <div class="preview-overlay">
              <span>已选择查询图像</span>
              <strong>{{ file?.name }}</strong>
            </div>
          </div>
          <div v-else class="upload-placeholder">
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <strong>拖拽图片到此处</strong>
            <span>或点击选择一张待检索的车辆图像</span>
          </div>
        </el-upload>

        <div class="query-toolbar">
          <div class="toolbar-copy">
            <strong>{{ file ? '图像已就绪' : '尚未选择图像' }}</strong>
            <span>{{ file ? '可以立即开始检索' : '支持 JPG / PNG 等常见格式' }}</span>
          </div>
          <el-button v-if="file" plain @click="resetQuery">清空图片</el-button>
        </div>
      </article>

      <article class="control-card">
        <div class="card-heading">
          <span class="section-kicker">Controls</span>
          <h3>检索参数</h3>
          <p>保留 Top-K 和时间范围位。时间过滤仍作为后续能力预留。</p>
        </div>

        <el-form label-position="top" class="control-form">
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

          <div class="hint-box">
            <span class="hint-title">当前说明</span>
            <p>模型选择与切换放在后台中进行；这里会同步展示当前激活的权重文件，方便前台确认。</p>
          </div>

          <div class="action-row">
            <el-button type="primary" class="search-button" :loading="loading" @click="handleSearch">
              {{ loading ? '正在执行检索...' : '开始检索' }}
            </el-button>
            <el-button plain @click="loadModelMeta">刷新模型信息</el-button>
          </div>
        </el-form>
      </article>
    </section>

    <section v-if="results.length > 0" class="results-panel">
      <div class="results-header">
        <div>
          <span class="section-kicker">Results</span>
          <h3>检索结果</h3>
        </div>
        <p>共找到 {{ results.length }} 条结果，用时 {{ timeCost }} 秒。</p>
      </div>

      <div class="results-grid">
        <article v-for="(item, index) in results" :key="`${item.img_url}-${index}`" class="result-card">
          <div class="result-image-wrap">
            <el-image
              :src="item.img_url"
              fit="cover"
              class="result-image"
              :preview-src-list="[item.img_url]"
              preview-teleported
              hide-on-click-modal
              lazy
            />
            <span class="score-pill" :class="getScoreClass(item.score)">
              {{ (item.score * 100).toFixed(1) }}%
            </span>
          </div>

          <div class="result-body">
            <h4>{{ item.vehicle_id }}</h4>
            <p>摄像头：{{ item.cam_id }}</p>
            <p>采集时间：{{ formatTime(item.capture_time) }}</p>
          </div>
        </article>
      </div>
    </section>

    <section v-else class="empty-panel">
      <template v-if="searched">
        <el-empty description="本次检索未返回结果，建议更换查询图像或增大结果数量。" />
      </template>
      <template v-else>
        <div class="empty-copy">
          <span class="section-kicker">Ready</span>
          <h3>系统已经准备好。</h3>
          <p>选择一张图像后即可开始检索。管理员可以从顶部按钮进入后台，进一步查看日志、同步图库和切换模型。</p>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { searchVehicle } from '@/api/search'
import { logout } from '@/api/auth'
import { fetchModelFiles } from '@/api/admin'

const router = useRouter()
const loading = ref(false)
const searched = ref(false)
const topK = ref(10)
const dateRange = ref([])
const file = ref(null)
const previewUrl = ref('')
const results = ref([])
const timeCost = ref(0)
const currentModel = ref('')

const isAdmin = computed(() => localStorage.getItem('user_role') === 'admin')
const currentModelLabel = computed(() => currentModel.value || '未读取到模型信息')
const bestScoreLabel = computed(() => {
  if (!results.value.length) {
    return '--'
  }
  return `${(results.value[0].score * 100).toFixed(1)}%`
})

const revokePreview = () => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

const handleFileChange = (uploadFile) => {
  revokePreview()
  file.value = uploadFile.raw
  previewUrl.value = URL.createObjectURL(uploadFile.raw)
  searched.value = false
  results.value = []
}

const resetQuery = () => {
  revokePreview()
  file.value = null
  searched.value = false
  results.value = []
  timeCost.value = 0
}

const handleSearch = async () => {
  if (!file.value) {
    ElMessage.warning('请先选择一张查询图像')
    return
  }

  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    formData.append('top_k', String(topK.value))

    const response = await searchVehicle(formData)
    results.value = response.data.results
    timeCost.value = response.data.time_cost
    searched.value = true
    ElMessage.success(`检索完成，共返回 ${response.data.total_found} 条结果`)
  } finally {
    loading.value = false
  }
}

const loadModelMeta = async () => {
  try {
    const response = await fetchModelFiles()
    currentModel.value = response.data.current_model_file
  } catch {
    currentModel.value = '模型信息读取失败'
  }
}

const getScoreClass = (score) => {
  if (score >= 0.8) {
    return 'score-high'
  }
  if (score >= 0.5) {
    return 'score-mid'
  }
  return 'score-low'
}

const formatTime = (value) => {
  if (!value) {
    return '未知'
  }
  return value.replace('T', ' ').slice(0, 19)
}

const goToAdmin = () => {
  router.push('/admin')
}

const handleLogout = async () => {
  try {
    await logout()
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}

onMounted(() => {
  loadModelMeta()
})

onBeforeUnmount(() => {
  revokePreview()
})
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  padding: 22px 28px 36px;
}

.topbar,
.hero-panel,
.query-card,
.control-card,
.results-panel,
.empty-panel {
  border: 1px solid var(--border);
  background: rgba(250, 249, 245, 0.9);
  box-shadow: var(--shadow-soft);
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 24px;
  border-radius: 24px;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-mark {
  width: 48px;
  height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: var(--brand);
  color: #faf9f5;
  font-family: var(--font-serif);
  font-size: 24px;
}

.brand-kicker,
.section-kicker,
.meta-label,
.hint-title {
  color: var(--brand);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 11px;
  font-weight: 600;
}

.brand-block h1 {
  margin: 4px 0 0;
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 500;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-pill {
  min-width: 168px;
  padding: 10px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid var(--border);
}

.meta-value {
  display: block;
  margin-top: 4px;
  color: var(--ink);
  font-size: 14px;
  font-weight: 600;
}

.model-value {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hero-panel {
  margin-top: 20px;
  padding: 34px;
  border-radius: 30px;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
  gap: 24px;
}

.hero-copy h2 {
  max-width: 11em;
  margin: 18px 0 14px;
  font-family: var(--font-serif);
  font-size: clamp(38px, 4vw, 56px);
  font-weight: 500;
  line-height: 1.08;
}

.hero-copy p {
  max-width: 700px;
  font-size: 17px;
  color: var(--ink-soft);
}

.hero-stats {
  display: grid;
  gap: 14px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border);
}

.stat-card span {
  color: var(--ink-muted);
  font-size: 13px;
}

.stat-card strong {
  font-family: var(--font-serif);
  font-size: 30px;
  font-weight: 500;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
  gap: 20px;
  margin-top: 20px;
}

.query-card,
.control-card,
.results-panel,
.empty-panel {
  border-radius: 28px;
  padding: 28px;
}

.card-heading h3,
.results-header h3,
.empty-copy h3 {
  margin: 14px 0 10px;
  font-family: var(--font-serif);
  font-size: 34px;
  font-weight: 500;
  line-height: 1.12;
}

.card-heading p,
.results-header p,
.empty-copy p {
  margin: 0;
  color: var(--ink-soft);
}

.query-upload {
  margin-top: 22px;
}

.query-upload :deep(.el-upload-dragger) {
  min-height: 340px;
  border-radius: 22px;
}

.preview-box {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 338px;
}

.preview-image {
  width: 100%;
  height: 100%;
  min-height: 338px;
  object-fit: cover;
  border-radius: 22px;
}

.preview-overlay {
  position: absolute;
  inset: auto 14px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(20, 20, 19, 0.72);
  color: #faf9f5;
  text-align: left;
}

.preview-overlay span {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(250, 249, 245, 0.7);
}

.upload-placeholder {
  min-height: 338px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--ink-soft);
}

.upload-icon {
  font-size: 42px;
  color: var(--brand);
}

.upload-placeholder strong {
  font-family: var(--font-serif);
  font-size: 30px;
  font-weight: 500;
  color: var(--ink);
}

.query-toolbar {
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.toolbar-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toolbar-copy span {
  color: var(--ink-muted);
  font-size: 14px;
}

.control-form {
  margin-top: 24px;
}

.hint-box {
  margin: 6px 0 24px;
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border);
}

.hint-box p {
  margin: 8px 0 0;
  color: var(--ink-soft);
  font-size: 14px;
}

.action-row {
  display: flex;
  gap: 12px;
}

.search-button {
  flex: 1;
  min-height: 48px;
}

.results-panel,
.empty-panel {
  margin-top: 20px;
}

.results-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 18px;
}

.result-card {
  overflow: hidden;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border);
}

.result-image-wrap {
  position: relative;
  height: 180px;
  overflow: hidden;
}

.result-image {
  width: 100%;
  height: 100%;
}

.score-pill {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.score-high {
  background: rgba(85, 113, 83, 0.18);
  color: #3f5e3d;
}

.score-mid {
  background: rgba(185, 133, 59, 0.18);
  color: #8b6428;
}

.score-low {
  background: rgba(181, 51, 51, 0.15);
  color: #9c2d2d;
}

.result-body {
  padding: 16px;
}

.result-body h4 {
  margin: 0 0 8px;
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 500;
}

.result-body p {
  margin: 0;
  color: var(--ink-soft);
  font-size: 14px;
}

.empty-copy {
  max-width: 720px;
}

@media (max-width: 1120px) {
  .hero-panel,
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .topbar-actions {
    flex-wrap: wrap;
  }
}

@media (max-width: 720px) {
  .search-page {
    padding: 16px;
  }

  .topbar,
  .hero-panel,
  .query-card,
  .control-card,
  .results-panel,
  .empty-panel {
    padding: 20px;
    border-radius: 22px;
  }

  .query-toolbar,
  .action-row,
  .results-header {
    flex-direction: column;
    align-items: stretch;
  }

  .meta-pill {
    width: 100%;
  }
}
</style>
