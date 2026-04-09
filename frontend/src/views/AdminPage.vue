<template>
  <div class="admin-page">
    <header class="admin-hero">
      <div class="hero-copy">
        <span class="section-kicker">Admin Console</span>
        <h1>后台控制台</h1>
        <p>保留日志、用户、图库、监控和系统配置能力，并补上模型管理入口，让管理员可以在同一套界面中完成运维操作。</p>
      </div>

      <div class="hero-actions">
        <div class="status-badge">
          <span>当前模型</span>
          <strong :title="modelState.current || '未读取'">{{ modelState.current || '未读取' }}</strong>
        </div>
        <el-button plain @click="router.push('/search')">返回前台</el-button>
        <el-button @click="handleLogout">退出登录</el-button>
      </div>
    </header>

    <div class="admin-shell">
      <aside class="nav-card">
        <button
          v-for="item in menuItems"
          :key="item.key"
          type="button"
          class="nav-item"
          :class="{ active: activeMenu === item.key }"
          @click="handleMenuSelect(item.key)"
        >
          <span class="nav-index">{{ item.index }}</span>
          <span class="nav-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ item.description }}</small>
          </span>
        </button>
      </aside>

      <main class="content-panel">
        <section v-if="activeMenu === 'logs'" class="panel-card">
          <div class="panel-header">
            <div>
              <span class="section-kicker">Logs</span>
              <h2>系统审计日志</h2>
            </div>
            <el-button plain @click="loadLogs">刷新日志</el-button>
          </div>

          <el-table :data="logList" v-loading="loadingLogs" style="width: 100%">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="user_id" label="用户 ID" width="100" />
            <el-table-column prop="operation" label="操作内容" min-width="320" />
            <el-table-column prop="status" label="结果" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status ? 'success' : 'danger'" effect="plain" round>
                  {{ scope.row.status ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="exec_time" label="执行时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.exec_time) }}
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrap">
            <el-pagination
              layout="prev, pager, next"
              :total="totalLogs"
              :page-size="pageSize"
              v-model:current-page="currentPage"
              @current-change="handlePageChange"
            />
          </div>
        </section>

        <section v-if="activeMenu === 'users'" class="panel-card">
          <div class="panel-header">
            <div>
              <span class="section-kicker">Users</span>
              <h2>账号与权限</h2>
            </div>
            <el-button type="primary" @click="showCreateDialog = true">新增账号</el-button>
          </div>

          <el-table :data="userList" v-loading="loadingUsers" style="width: 100%">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="username" label="用户名" min-width="180" />
            <el-table-column prop="role" label="角色" width="140">
              <template #default="scope">
                <el-tag :type="scope.row.role === 'admin' ? 'warning' : 'info'" effect="plain" round>
                  {{ scope.row.role === 'admin' ? '管理员' : '普通用户' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="创建时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.create_time) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button plain @click="handleDeleteUser(scope.row.id)" :disabled="scope.row.id === 1">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section v-if="activeMenu === 'gallery'" class="panel-card">
          <div class="panel-header">
            <div>
              <span class="section-kicker">Gallery</span>
              <h2>图库特征同步</h2>
            </div>
            <div class="header-actions">
              <el-button type="primary" :disabled="isEngineRunning" @click="handleSyncGallery">增量同步</el-button>
              <el-button plain :disabled="isEngineRunning" @click="handleRebuildGallery">全量重建</el-button>
              <el-button plain :disabled="isEngineRunning" @click="handleClearGallery">清空图库</el-button>
            </div>
          </div>

          <div class="gallery-status-row">
            <article class="mini-stat">
              <span>同步状态</span>
              <strong>{{ isEngineRunning ? '运行中' : '空闲' }}</strong>
            </article>
            <article class="mini-stat">
              <span>日志行数</span>
              <strong>{{ engineLogs.length }}</strong>
            </article>
          </div>

          <div class="terminal-shell">
            <div class="terminal-top">
              <div class="lights">
                <span class="light red"></span>
                <span class="light yellow"></span>
                <span class="light green"></span>
              </div>
              <span>Gallery Pipeline</span>
            </div>
            <div ref="terminalRef" class="terminal-body">
              <div v-for="(log, index) in engineLogs" :key="index" class="terminal-line">
                {{ log }}
              </div>
              <div v-if="isEngineRunning" class="terminal-line">...</div>
            </div>
          </div>
        </section>

        <section v-if="activeMenu === 'monitor'" class="panel-card">
          <div class="panel-header">
            <div>
              <span class="section-kicker">Monitor</span>
              <h2>运行状态总览</h2>
            </div>
            <el-button plain :loading="loadingStats" @click="loadStats">刷新统计</el-button>
          </div>

          <div class="stats-grid">
            <article class="stat-card">
              <span>图库图片总数</span>
              <strong>{{ sysStats.total_images }}</strong>
            </article>
            <article class="stat-card">
              <span>唯一车辆 ID</span>
              <strong>{{ sysStats.total_vehicles }}</strong>
            </article>
            <article class="stat-card">
              <span>最近入库时间</span>
              <strong class="small">{{ sysStats.latest_ingestion_time }}</strong>
            </article>
            <article class="stat-card">
              <span>模型已初始化</span>
              <strong>{{ modelState.initialized ? '是' : '否' }}</strong>
            </article>
          </div>
        </section>

        <section v-if="activeMenu === 'settings'" class="panel-card settings-panel">
          <div class="panel-header">
            <div>
              <span class="section-kicker">Settings</span>
              <h2>系统参数配置</h2>
            </div>
          </div>

          <el-form :model="sysConfig" label-position="top">
            <el-form-item label="模型设备">
              <el-select v-model="sysConfig.model_device">
                <el-option label="CPU" value="cpu" />
                <el-option label="CUDA" value="cuda" />
              </el-select>
            </el-form-item>

            <el-form-item label="日志级别">
              <el-select v-model="sysConfig.log_level">
                <el-option label="DEBUG" value="DEBUG" />
                <el-option label="INFO" value="INFO" />
                <el-option label="WARNING" value="WARNING" />
                <el-option label="ERROR" value="ERROR" />
              </el-select>
            </el-form-item>

            <el-form-item label="相似度阈值">
              <el-slider v-model="sysConfig.similarity_threshold" :min="0" :max="1" :step="0.01" show-input />
            </el-form-item>

            <el-form-item label="最多返回结果数">
              <el-input-number v-model="sysConfig.max_results" :min="10" :max="500" />
            </el-form-item>

            <div class="support-note">
              <strong>说明</strong>
              <p>这里保存的是系统运行参数；模型权重的即时切换已经拆分到“模型管理”页中，避免配置和运行态混在一起。</p>
            </div>

            <div class="form-actions">
              <el-button type="primary" :loading="savingConfig" @click="handleSaveConfig">保存配置</el-button>
              <el-button plain @click="handleMenuSelect('models')">前往模型管理</el-button>
            </div>
          </el-form>
        </section>

        <section v-if="activeMenu === 'models'" class="panel-card">
          <div class="panel-header">
            <div>
              <span class="section-kicker">Models</span>
              <h2>模型管理</h2>
            </div>
            <div class="header-actions">
              <el-button plain :loading="loadingModels" @click="loadModels">刷新模型列表</el-button>
              <el-button type="primary" :disabled="!selectedModelFile || selectedModelFile === modelState.current" @click="handleSelectModel">
                应用模型
              </el-button>
            </div>
          </div>

          <div class="stats-grid model-summary">
            <article class="stat-card">
              <span>当前模型</span>
              <strong class="small">{{ modelState.current || '未加载' }}</strong>
            </article>
            <article class="stat-card">
              <span>运行设备</span>
              <strong>{{ modelState.device || '未知' }}</strong>
            </article>
            <article class="stat-card">
              <span>引擎状态</span>
              <strong>{{ modelState.initialized ? '已初始化' : '未初始化' }}</strong>
            </article>
            <article class="stat-card">
              <span>可选模型数</span>
              <strong>{{ modelFiles.length }}</strong>
            </article>
          </div>

          <div class="model-selector">
            <el-form label-position="top">
              <el-form-item label="选择权重文件">
                <el-select v-model="selectedModelFile" filterable placeholder="请选择一个模型权重">
                  <el-option v-for="item in modelFiles" :key="item" :label="item" :value="item" />
                </el-select>
              </el-form-item>
            </el-form>

            <div class="support-note">
              <strong>使用建议</strong>
              <p>前台检索页会同步展示这里当前激活的模型文件。切换后如果引擎已经初始化，后台会立即重新配置。</p>
            </div>
          </div>
        </section>
      </main>
    </div>

    <el-dialog v-model="showCreateDialog" title="新增账号" width="420px">
      <el-form :model="newUserForm" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="newUserForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="newUserForm.password" type="password" show-password autocomplete="off" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="newUserForm.role">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button plain @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" :loading="creatingUser" @click="handleCreateUser">创建</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  clearGalleryData,
  createNewUser,
  fetchAuditLogs,
  fetchGalleryStatus,
  fetchModelFiles,
  fetchSysConfig,
  fetchSystemStats,
  fetchUserList,
  rebuildGalleryData,
  removeUser,
  selectModelFile,
  syncGalleryData,
  updateSysConfig
} from '@/api/admin'
import { logout } from '@/api/auth'

const router = useRouter()
const activeMenu = ref('logs')

const menuItems = [
  { key: 'logs', index: '01', label: '日志', description: '查看系统审计记录' },
  { key: 'users', index: '02', label: '账号', description: '维护登录与权限' },
  { key: 'gallery', index: '03', label: '图库', description: '同步与重建图库特征' },
  { key: 'monitor', index: '04', label: '监控', description: '查看数据与运行状态' },
  { key: 'settings', index: '05', label: '配置', description: '保存系统参数' },
  { key: 'models', index: '06', label: '模型', description: '选择和应用权重文件' }
]

const loadingLogs = ref(false)
const loadingUsers = ref(false)
const loadingStats = ref(false)
const loadingConfig = ref(false)
const savingConfig = ref(false)
const loadingModels = ref(false)

const logList = ref([])
const totalLogs = ref(0)
const currentPage = ref(1)
const pageSize = ref(15)

const userList = ref([])
const showCreateDialog = ref(false)
const creatingUser = ref(false)
const newUserForm = reactive({
  username: '',
  password: '',
  role: 'user'
})

const sysStats = reactive({
  total_images: 0,
  total_vehicles: 0,
  latest_ingestion_time: '暂无记录'
})

const sysConfig = reactive({
  model_device: 'cpu',
  similarity_threshold: 0.5,
  max_results: 50,
  log_level: 'INFO'
})

const modelFiles = ref([])
const selectedModelFile = ref('')
const modelState = reactive({
  current: '',
  initialized: false,
  device: ''
})

const isEngineRunning = ref(false)
const engineLogs = ref([])
const terminalRef = ref(null)
let pollTimer = null

const currentMenuTitle = computed(() => menuItems.find((item) => item.key === activeMenu.value)?.label || '')

const resetPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const scrollTerminalToBottom = async () => {
  await nextTick()
  if (terminalRef.value) {
    terminalRef.value.scrollTop = terminalRef.value.scrollHeight
  }
}

const handleMenuSelect = async (key) => {
  activeMenu.value = key

  if (key !== 'gallery') {
    resetPolling()
  }

  if (key === 'gallery') {
    await pollEngineStatus()
    if (isEngineRunning.value && !pollTimer) {
      pollTimer = setInterval(pollEngineStatus, 1500)
    }
  }

  if (key === 'monitor') {
    loadStats()
  }

  if (key === 'settings') {
    loadConfig()
  }

  if (key === 'models') {
    loadModels()
  }
}

const loadLogs = async () => {
  loadingLogs.value = true
  try {
    const response = await fetchAuditLogs(currentPage.value, pageSize.value)
    logList.value = response.data.items
    totalLogs.value = response.data.total
  } finally {
    loadingLogs.value = false
  }
}

const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const response = await fetchUserList()
    userList.value = response.data
  } finally {
    loadingUsers.value = false
  }
}

const loadStats = async () => {
  loadingStats.value = true
  try {
    const response = await fetchSystemStats()
    sysStats.total_images = response.data.total_images
    sysStats.total_vehicles = response.data.total_vehicles
    sysStats.latest_ingestion_time = response.data.latest_ingestion_time
  } finally {
    loadingStats.value = false
  }
}

const loadConfig = async () => {
  loadingConfig.value = true
  try {
    const response = await fetchSysConfig()
    Object.assign(sysConfig, response.data)
  } finally {
    loadingConfig.value = false
  }
}

const loadModels = async () => {
  loadingModels.value = true
  try {
    const response = await fetchModelFiles()
    modelFiles.value = response.data.available_models || []
    modelState.current = response.data.current_model_file || ''
    modelState.initialized = Boolean(response.data.initialized)
    modelState.device = response.data.model_device || ''
    selectedModelFile.value = modelState.current
  } finally {
    loadingModels.value = false
  }
}

const handleSaveConfig = async () => {
  savingConfig.value = true
  try {
    await updateSysConfig(sysConfig)
    ElMessage.success('系统配置已保存')
  } finally {
    savingConfig.value = false
  }
}

const handleSelectModel = async () => {
  if (!selectedModelFile.value) {
    ElMessage.warning('请先选择一个模型文件')
    return
  }

  await selectModelFile({ model_file: selectedModelFile.value })
  modelState.current = selectedModelFile.value
  ElMessage.success('模型切换成功')
  loadModels()
}

const pollEngineStatus = async () => {
  try {
    const response = await fetchGalleryStatus()
    isEngineRunning.value = response.data.is_running
    engineLogs.value = response.data.logs
    await scrollTerminalToBottom()

    if (!isEngineRunning.value) {
      resetPolling()
    }
  } catch {
    resetPolling()
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadLogs()
}

const handleSyncGallery = async () => {
  await syncGalleryData()
  ElMessage.success('已启动增量同步任务')
  if (!pollTimer) {
    pollTimer = setInterval(pollEngineStatus, 1500)
  }
  pollEngineStatus()
}

const handleRebuildGallery = async () => {
  await ElMessageBox.confirm('全量重建会清空现有图库特征并重新计算，确认继续吗？', '确认重建', {
    confirmButtonText: '继续',
    cancelButtonText: '取消',
    type: 'warning'
  })
  await rebuildGalleryData()
  ElMessage.success('已启动全量重建任务')
  if (!pollTimer) {
    pollTimer = setInterval(pollEngineStatus, 1500)
  }
  pollEngineStatus()
}

const handleClearGallery = async () => {
  await ElMessageBox.confirm('此操作会清空数据库中的图库特征，且不可恢复。确认继续吗？', '高风险操作', {
    confirmButtonText: '确认清空',
    cancelButtonText: '取消',
    type: 'error'
  })
  await clearGalleryData()
  ElMessage.success('图库特征已清空')
  pollEngineStatus()
}

const resetCreateForm = () => {
  newUserForm.username = ''
  newUserForm.password = ''
  newUserForm.role = 'user'
}

const handleCreateUser = async () => {
  if (!newUserForm.username || !newUserForm.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }

  creatingUser.value = true
  try {
    await createNewUser(newUserForm)
    ElMessage.success('账号创建成功')
    showCreateDialog.value = false
    resetCreateForm()
    loadUsers()
  } finally {
    creatingUser.value = false
  }
}

const handleDeleteUser = async (id) => {
  await ElMessageBox.confirm('确认删除该账号吗？', '删除账号', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  })
  await removeUser(id)
  ElMessage.success('账号已删除')
  loadUsers()
}

const handleLogout = async () => {
  try {
    await logout()
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    router.push('/login')
  }
}

const formatTime = (value) => {
  if (!value) {
    return '未知'
  }
  return value.replace('T', ' ').slice(0, 19)
}

onMounted(async () => {
  await Promise.all([loadLogs(), loadUsers(), loadModels()])
})

onBeforeUnmount(() => {
  resetPolling()
})
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  padding: 24px 28px 36px;
}

.admin-hero,
.nav-card,
.panel-card {
  border: 1px solid var(--border);
  background: rgba(250, 249, 245, 0.92);
  box-shadow: var(--shadow-soft);
}

.admin-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 30px;
  border-radius: 30px;
}

.section-kicker {
  color: var(--brand);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 12px;
  font-weight: 600;
}

.hero-copy h1 {
  margin: 14px 0 10px;
  font-family: var(--font-serif);
  font-size: 52px;
  font-weight: 500;
  line-height: 1.05;
}

.hero-copy p {
  max-width: 760px;
  margin: 0;
  color: var(--ink-soft);
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  max-width: 300px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid var(--border);
}

.status-badge span {
  display: block;
  color: var(--brand);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

.status-badge strong {
  display: block;
  margin-top: 6px;
  font-size: 14px;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-shell {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 20px;
  margin-top: 20px;
}

.nav-card {
  padding: 18px;
  border-radius: 28px;
  align-self: start;
  position: sticky;
  top: 20px;
}

.nav-item {
  width: 100%;
  display: flex;
  gap: 14px;
  padding: 14px;
  border: 0;
  border-radius: 18px;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.nav-item + .nav-item {
  margin-top: 8px;
}

.nav-item:hover {
  background: rgba(201, 100, 66, 0.06);
}

.nav-item.active {
  background: rgba(201, 100, 66, 0.12);
  box-shadow: 0 0 0 1px rgba(201, 100, 66, 0.22) inset;
}

.nav-index {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--brand);
  font-size: 12px;
  font-weight: 700;
}

.nav-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-copy strong {
  color: var(--ink);
  font-size: 16px;
}

.nav-copy small {
  color: var(--ink-muted);
  line-height: 1.45;
}

.content-panel {
  min-width: 0;
}

.panel-card {
  padding: 26px;
  border-radius: 28px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.panel-header h2 {
  margin: 12px 0 0;
  font-family: var(--font-serif);
  font-size: 38px;
  font-weight: 500;
  line-height: 1.08;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.gallery-status-row,
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.mini-stat,
.stat-card {
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid var(--border);
}

.mini-stat span,
.stat-card span {
  display: block;
  color: var(--ink-muted);
  font-size: 13px;
}

.mini-stat strong,
.stat-card strong {
  display: block;
  margin-top: 8px;
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 500;
}

.stat-card strong.small {
  font-size: 22px;
  line-height: 1.3;
}

.terminal-shell {
  margin-top: 20px;
  overflow: hidden;
  border-radius: 22px;
  background: #1c1b1a;
  border: 1px solid #2d2b28;
}

.terminal-top {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #242320;
  color: #b0aea5;
  border-bottom: 1px solid #2d2b28;
}

.lights {
  display: flex;
  gap: 8px;
}

.light {
  width: 11px;
  height: 11px;
  border-radius: 999px;
}

.light.red {
  background: #c66464;
}

.light.yellow {
  background: #d1a256;
}

.light.green {
  background: #648f60;
}

.terminal-body {
  height: 420px;
  overflow: auto;
  padding: 18px;
  color: #d9d4ca;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.65;
}

.terminal-line + .terminal-line {
  margin-top: 4px;
}

.settings-panel {
  max-width: 760px;
}

.support-note {
  margin: 6px 0 24px;
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.58);
  border: 1px solid var(--border);
}

.support-note strong {
  display: block;
  margin-bottom: 6px;
}

.support-note p {
  margin: 0;
  color: var(--ink-soft);
}

.form-actions,
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.model-summary {
  margin-bottom: 20px;
}

.model-selector {
  max-width: 760px;
}

@media (max-width: 1180px) {
  .admin-shell {
    grid-template-columns: 1fr;
  }

  .nav-card {
    position: static;
  }
}

@media (max-width: 860px) {
  .admin-page {
    padding: 16px;
  }

  .admin-hero,
  .panel-card,
  .nav-card {
    padding: 20px;
    border-radius: 22px;
  }

  .admin-hero,
  .panel-header {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-actions,
  .header-actions,
  .form-actions,
  .dialog-footer {
    flex-wrap: wrap;
  }
}
</style>
