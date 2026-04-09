<template>
  <div class="app-page">
    <div class="app-shell">
      <PageHeader
        eyebrow="Admin Console"
        title="后台控制台"
        description="后台继续保留日志、用户、图库、监控和配置五项能力，但界面组织得更清楚，操作说明也更直白。"
      >
        <template #meta>
          <div class="header-meta">
            <span class="app-chip"><strong>{{ isRunning ? '正在处理' : '当前空闲' }}</strong> 图库状态</span>
          </div>
        </template>

        <template #actions>
          <el-button plain @click="router.push('/search')">返回前台</el-button>
          <el-button @click="handleLogout">退出登录</el-button>
        </template>
      </PageHeader>

      <div class="admin-layout">
        <AdminNav :items="menuItems" :active-key="activeMenu" @select="handleMenuSelect" />

        <div class="admin-content">
          <SectionCard
            v-if="activeMenu === 'logs'"
            eyebrow="Logs"
            title="系统操作日志"
            description="按时间顺序查看登录、检索和后台操作记录，方便管理员追踪关键行为。"
          >
            <template #actions>
              <ActionBar align="right">
                <el-button plain :loading="loadingLogs" @click="loadLogs">刷新日志</el-button>
              </ActionBar>
            </template>

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
                  {{ formatDateTime(scope.row.exec_time) }}
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
          </SectionCard>

          <SectionCard
            v-if="activeMenu === 'users'"
            eyebrow="Users"
            title="账号与权限"
            description="维护系统账号、角色和创建时间，避免把权限信息散落在多个页面里。"
          >
            <template #actions>
              <ActionBar align="right">
                <el-button plain :loading="loadingUsers" @click="loadUsers">刷新列表</el-button>
                <el-button type="primary" @click="showCreateDialog = true">新增账号</el-button>
              </ActionBar>
            </template>

            <el-table :data="userList" v-loading="loadingUsers" style="width: 100%">
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="username" label="用户名" min-width="180" />
              <el-table-column prop="role" label="角色" width="140">
                <template #default="scope">
                  <el-tag
                    effect="plain"
                    round
                    class="role-tag"
                    :class="scope.row.role === 'admin' ? 'role-admin' : 'role-user'"
                  >
                    {{ scope.row.role === 'admin' ? '管理员' : '普通用户' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="create_time" label="创建时间" width="180">
                <template #default="scope">
                  {{ formatDateTime(scope.row.create_time) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="scope">
                  <el-button plain :disabled="scope.row.id === 1" @click="handleDeleteUser(scope.row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </SectionCard>

          <SectionCard
            v-if="activeMenu === 'gallery'"
            eyebrow="Gallery"
            title="更新图库数据"
            description="在这里处理新图片、重新处理全部图片，或者清空现有记录，并同时查看运行日志。"
          >
            <template #meta>
              <span class="section-chip">{{ isRunning ? '正在处理图库' : '当前空闲' }}</span>
            </template>

            <template #actions>
              <ActionBar align="right">
                <el-button type="primary" :disabled="isRunning" @click="handleSyncGallery">同步新图片</el-button>
                <el-button plain :disabled="isRunning" @click="handleRebuildGallery">重新处理全部图片</el-button>
                <el-button plain :disabled="isRunning" @click="handleClearGallery">清空图库记录</el-button>
              </ActionBar>
            </template>

            <div class="stats-grid compact-grid">
              <StatCard label="任务状态" :value="isRunning ? '运行中' : '空闲'" />
              <StatCard label="日志行数" :value="String(logs.length)" />
            </div>

            <StatusBanner
              tone="warning"
              title="请谨慎操作"
              message="重新处理全部图片会先清空现有特征再重新计算；清空图库记录会直接删除数据库里的图库特征。"
            />

            <StatusBanner
              v-if="galleryErrorMessage"
              tone="danger"
              title="图库状态读取失败"
              :message="galleryErrorMessage"
            />

            <TerminalLogPanel class="top-gap" title="图库处理日志" :logs="logs" :is-running="isRunning" />
          </SectionCard>

          <SectionCard
            v-if="activeMenu === 'monitor'"
            eyebrow="Monitor"
            title="运行状态总览"
            description="把图库规模、最近入库时间和模型初始化状态整理成轻量统计卡片，便于快速查看。"
          >
            <template #actions>
              <ActionBar align="right">
                <el-button plain :loading="loadingStats" @click="loadStats">刷新统计</el-button>
              </ActionBar>
            </template>

            <div class="stats-grid">
              <StatCard label="图库图片总数" :value="String(sysStats.total_images)" />
              <StatCard label="唯一车辆 ID" :value="String(sysStats.total_vehicles)" />
              <StatCard label="最近入库时间" :value="sysStats.latest_ingestion_time" />
              <StatCard label="引擎状态" :value="modelState.initialized ? '已初始化' : '未初始化'" />
            </div>
          </SectionCard>

          <SectionCard
            v-if="activeMenu === 'settings'"
            eyebrow="Settings"
            title="系统配置与默认模型"
            description="这里分别管理系统运行参数和默认模型，避免把临时切换和长期设置混在一起。"
          >
            <div class="settings-grid">
              <article class="settings-panel">
                <div class="settings-copy">
                  <h3>系统参数</h3>
                  <p>这里保存运行设备、日志级别、相似度阈值和最大返回结果数。</p>
                </div>

                <el-form :model="sysConfig" label-position="top" class="settings-form">
                  <el-form-item label="运行设备">
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

                  <el-form-item label="最大返回结果数">
                    <el-input-number v-model="sysConfig.max_results" :min="10" :max="500" />
                  </el-form-item>
                </el-form>

                <StatusBanner
                  tone="info"
                  title="保存后会立即尝试生效"
                  message="如果切换运行设备失败，界面会直接提示原因；保存成功后，这里的显示会按后端当前真实状态刷新。"
                />

                <ActionBar align="left">
                  <el-button type="primary" :loading="savingConfig" @click="handleSaveConfig">保存系统配置</el-button>
                  <el-button plain :loading="loadingConfig" @click="loadConfig">重新读取配置</el-button>
                </ActionBar>
              </article>

              <article class="settings-panel">
                <div class="settings-copy">
                  <h3>默认模型</h3>
                  <p>这里设置系统启动时优先使用的模型文件，与前台当前运行模型分开管理。</p>
                </div>

                <div class="stats-grid compact-grid">
                  <StatCard label="当前运行模型" :value="modelState.current || '未读取到模型'" mono />
                  <StatCard label="默认模型" :value="modelState.default || '未设置'" mono />
                </div>

                <el-form label-position="top" class="settings-form">
                  <el-form-item label="选择默认模型">
                    <el-select v-model="selectedModelFile" filterable placeholder="请选择一个模型文件">
                      <el-option v-for="item in modelFiles" :key="item" :label="item" :value="item" />
                    </el-select>
                  </el-form-item>
                </el-form>

                <StatusBanner
                  tone="info"
                  title="默认模型只影响系统启动偏好"
                  message="保存后会更新系统默认选择；如果当前引擎已经初始化，后端会按现有逻辑重新加载模型。"
                />

                <StatusBanner
                  v-if="modelErrorMessage"
                  tone="danger"
                  title="模型信息同步失败"
                  :message="modelErrorMessage"
                />

                <ActionBar align="left">
                  <el-button plain :loading="loadingModels" @click="loadSettingsContext">刷新模型信息</el-button>
                  <el-button
                    type="primary"
                    :loading="applyingModel"
                    :disabled="!selectedModelFile || selectedModelFile === modelState.default"
                    @click="handleSaveDefaultModel"
                  >
                    保存默认模型
                  </el-button>
                </ActionBar>
              </article>
            </div>
          </SectionCard>
        </div>
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
          <ActionBar align="right">
            <el-button plain @click="showCreateDialog = false">取消</el-button>
            <el-button type="primary" :loading="creatingUser" @click="handleCreateUser">创建账号</el-button>
          </ActionBar>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ActionBar from '@/components/base/ActionBar.vue'
import PageHeader from '@/components/base/PageHeader.vue'
import SectionCard from '@/components/base/SectionCard.vue'
import StatCard from '@/components/base/StatCard.vue'
import StatusBanner from '@/components/base/StatusBanner.vue'
import AdminNav from '@/components/admin/AdminNav.vue'
import TerminalLogPanel from '@/components/admin/TerminalLogPanel.vue'
import { useGalleryPolling } from '@/composables/useGalleryPolling'
import { useModelMeta } from '@/composables/useModelMeta'
import { useSession } from '@/composables/useSession'
import {
  createNewUser,
  clearGalleryData,
  fetchAuditLogs,
  fetchSysConfig,
  fetchSystemStats,
  fetchUserList,
  rebuildGalleryData,
  removeUser,
  syncGalleryData,
  updateSysConfig
} from '@/api/admin'
import { formatDateTime } from '@/utils/formatters'

const router = useRouter()
const { syncSession, logoutAndRedirect } = useSession(router)
const {
  isRunning,
  logs,
  errorMessage: galleryErrorMessage,
  refreshStatus,
  startPolling,
  stopPolling
} = useGalleryPolling()
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

const activeMenu = ref('logs')
const loadingLogs = ref(false)
const loadingUsers = ref(false)
const loadingStats = ref(false)
const loadingConfig = ref(false)
const savingConfig = ref(false)
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

const menuItems = [
  { key: 'logs', index: '01', label: '日志', description: '查看系统操作记录' },
  { key: 'users', index: '02', label: '账号', description: '维护登录账号与权限' },
  { key: 'gallery', index: '03', label: '图库', description: '处理新图片或重建图库' },
  { key: 'monitor', index: '04', label: '监控', description: '查看图库规模与运行状态' },
  { key: 'settings', index: '05', label: '配置', description: '保存系统参数与默认模型' }
]

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

const loadSettingsContext = async () => {
  try {
    await Promise.all([
      loadConfig(),
      loadModelMeta({ selectionTarget: 'default' })
    ])
  } catch {
    // Inline status banners already describe model failures.
  }
}

const handleMenuSelect = async (key) => {
  activeMenu.value = key

  if (key !== 'gallery') {
    stopPolling()
  }

  if (key === 'logs') {
    await loadLogs()
    return
  }

  if (key === 'users') {
    await loadUsers()
    return
  }

  if (key === 'gallery') {
    try {
      await refreshStatus()
      if (isRunning.value) {
        startPolling()
      }
    } catch {
      // Inline banner already describes the failure state.
    }
    return
  }

  if (key === 'monitor') {
    await loadStats()
    return
  }

  if (key === 'settings') {
    await loadSettingsContext()
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadLogs()
}

const handleSaveConfig = async () => {
  savingConfig.value = true

  try {
    await updateSysConfig(sysConfig)
    await Promise.all([
      loadConfig(),
      loadModelMeta({ selectionTarget: 'default' })
    ])
    ElMessage.success('系统配置已保存。')
  } finally {
    savingConfig.value = false
  }
}

const handleSaveDefaultModel = async () => {
  if (!selectedModelFile.value) {
    ElMessage.warning('请先选择一个默认模型。')
    return
  }

  try {
    await applySelectedModel({ setAsDefault: true })
    ElMessage.success('默认模型已更新。')
  } catch {
    // Error state is handled inline and by the request layer.
  }
}

const handleSyncGallery = async () => {
  await syncGalleryData()
  ElMessage.success('已开始处理新导入的图片。')
  startPolling()
}

const handleRebuildGallery = async () => {
  await ElMessageBox.confirm(
    '这会先清空现有图库特征，再重新处理全部图片。确认继续吗？',
    '确认重新处理',
    {
      confirmButtonText: '继续',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )

  await rebuildGalleryData()
  ElMessage.success('已开始重新处理全部图库图片。')
  startPolling()
}

const handleClearGallery = async () => {
  await ElMessageBox.confirm(
    '此操作会删除数据库中的图库特征记录，且不可恢复。确认继续吗？',
    '高风险操作',
    {
      confirmButtonText: '确认清空',
      cancelButtonText: '取消',
      type: 'error'
    }
  )

  await clearGalleryData()
  ElMessage.success('图库记录已清空。')
  await refreshStatus()
}

const resetCreateForm = () => {
  newUserForm.username = ''
  newUserForm.password = ''
  newUserForm.role = 'user'
}

const handleCreateUser = async () => {
  if (!newUserForm.username || !newUserForm.password) {
    ElMessage.warning('请填写用户名和密码。')
    return
  }

  creatingUser.value = true

  try {
    await createNewUser(newUserForm)
    ElMessage.success('账号创建成功。')
    showCreateDialog.value = false
    resetCreateForm()
    await loadUsers()
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
  ElMessage.success('账号已删除。')
  await loadUsers()
}

const handleLogout = async () => {
  await logoutAndRedirect()
  ElMessage.success('已退出登录。')
}

onMounted(async () => {
  syncSession()

  try {
    await Promise.all([
      loadLogs(),
      loadUsers(),
      loadConfig(),
      loadModelMeta({ selectionTarget: 'default' })
    ])
  } catch {
    // Inline status banners already show the relevant error states.
  }
})
</script>

<style scoped>
.header-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.admin-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 20px;
}

.admin-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

.section-chip {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.58);
  color: var(--text-secondary);
  font-size: 13px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.compact-grid {
  margin-bottom: 18px;
}

.top-gap {
  margin-top: 18px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px;
  border: 1px solid var(--border-soft);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.56);
}

.settings-copy h3 {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 500;
}

.settings-copy p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.settings-form {
  margin: 0;
}

.role-tag {
  border-color: var(--border-strong);
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.7);
}

.role-admin {
  color: #8b6428;
  border-color: rgba(185, 133, 59, 0.28);
  background: rgba(185, 133, 59, 0.1);
}

.role-user {
  color: var(--text-secondary);
  border-color: rgba(209, 207, 197, 0.9);
  background: rgba(255, 255, 255, 0.72);
}

@media (max-width: 1180px) {
  .admin-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
