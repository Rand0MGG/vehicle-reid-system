<template>
  <div class="app-page">
    <div class="app-shell">
      <PageHeader
        eyebrow="Admin Console"
        title="后台控制台"
        description="后台集中处理日志、用户、图库任务、运行监控和系统设置，并明确标记当前模型与图库特征模型是否一致。"
      >
        <template #meta>
          <div class="header-meta">
            <span class="app-chip">图库任务 <strong>{{ isRunning ? '运行中' : '当前空闲' }}</strong></span>
            <span class="app-chip">当前模型 <strong>{{ modelState.current || '未记录' }}</strong></span>
          </div>
        </template>

        <template #actions>
          <el-button plain @click="router.push('/search')">返回前台</el-button>
          <el-button @click="handleLogout">退出登录</el-button>
        </template>
      </PageHeader>

      <StatusBanner
        v-if="galleryMismatch"
        tone="warning"
        title="当前模型与图库特征模型不一致"
        :message="`当前模型为 ${modelState.current || '未记录'}，图库特征仍由 ${modelState.gallery || '未记录'} 计算。请先重新处理全部图片。`"
      />

      <StatusBanner
        v-else-if="galleryModelUnknown"
        tone="warning"
        title="图库特征模型尚未记录"
        message="当前图库已有特征数据，但还没有记录它是由哪个模型计算得到的。建议先重新处理全部图片一次。"
      />

      <div class="admin-layout">
        <AdminNav :items="menuItems" :active-key="activeMenu" @select="handleMenuSelect" />

        <div class="admin-content">
          <SectionCard
            v-if="activeMenu === 'settings'"
            eyebrow="Settings"
            title="系统配置与当前模型"
            description="这里统一维护运行设备、阈值、返回结果数量，以及后台当前使用的模型。"
          >
            <div class="settings-grid">
              <article class="settings-panel">
                <div class="settings-copy">
                  <h3>系统参数</h3>
                  <p>这些设置会保存到本地配置中，服务重启后继续生效。</p>
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

                <ActionBar>
                  <el-button type="primary" :loading="savingConfig" @click="handleSaveConfig">保存系统参数</el-button>
                  <el-button plain :loading="loadingConfig" @click="loadConfig">重新读取</el-button>
                </ActionBar>
              </article>

              <article class="settings-panel">
                <div class="settings-copy">
                  <h3>当前模型</h3>
                  <p>模型只能由管理员切换。切换后如果与图库特征模型不一致，系统会提醒你重新处理全部图片。</p>
                </div>

                <div class="model-state-grid">
                  <StatCard label="当前模型" :value="modelState.current || '未记录'" mono />
                  <StatCard label="图库特征模型" :value="modelState.gallery || '尚未记录'" mono />
                  <StatCard label="运行设备" :value="modelState.device || '未知'" />
                </div>

                <el-form label-position="top" class="settings-form top-gap">
                  <el-form-item label="选择当前模型">
                    <el-select v-model="selectedModelFile" placeholder="请选择一个模型文件">
                      <el-option
                        v-for="item in modelFiles"
                        :key="item"
                        :label="item"
                        :value="item"
                      />
                    </el-select>
                  </el-form-item>
                </el-form>

                <ActionBar>
                  <el-button plain :loading="modelLoading" @click="reloadModelMeta">刷新模型列表</el-button>
                  <el-button
                    type="primary"
                    :loading="applying"
                    :disabled="!selectedModelFile || selectedModelFile === modelState.current"
                    @click="handleApplyModel"
                  >
                    应用当前模型
                  </el-button>
                </ActionBar>
              </article>
            </div>
          </SectionCard>

          <SectionCard
            v-if="activeMenu === 'gallery'"
            eyebrow="Gallery"
            title="图库数据处理"
            description="在这里处理新图片、重新处理全部图片，或清空已有图库特征记录。"
          >
            <template #meta>
              <span class="app-chip"><strong>{{ isRunning ? '处理中' : '空闲' }}</strong> 图库状态</span>
            </template>

            <template #actions>
              <ActionBar align="right">
                <el-button type="primary" :disabled="isRunning || syncBlocked" @click="handleSyncGallery">处理新增图片</el-button>
                <el-button plain :disabled="isRunning" @click="handleRebuildGallery">重新处理全部图片</el-button>
                <el-button plain :disabled="isRunning" @click="handleClearGallery">清空图库记录</el-button>
              </ActionBar>
            </template>

            <div class="stats-grid compact-grid">
              <StatCard label="任务状态" :value="isRunning ? '运行中' : '空闲'" />
              <StatCard label="当前模型" :value="modelState.current || '未记录'" mono />
              <StatCard label="图库特征模型" :value="modelState.gallery || '尚未记录'" mono />
            </div>

            <StatusBanner
              v-if="syncBlocked"
              tone="warning"
              title="当前不能直接处理新增图片"
              :message="syncBlockedMessage"
            />

            <StatusBanner
              v-if="galleryErrorMessage"
              tone="danger"
              title="图库状态读取失败"
              :message="galleryErrorMessage"
            />

            <div class="top-gap">
              <TerminalLogPanel title="图库处理日志" :logs="logs" :is-running="isRunning" />
            </div>
          </SectionCard>

          <SectionCard
            v-if="activeMenu === 'monitor'"
            eyebrow="Monitor"
            title="运行状态总览"
            description="把图库规模、最近入库时间和模型状态整理成轻量统计卡片，便于快速查看。"
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
            v-if="activeMenu === 'logs'"
            eyebrow="Logs"
            title="系统操作日志"
            description="按时间顺序查看登录、检索和后台操作记录。"
          >
            <template #actions>
              <ActionBar align="right">
                <el-button plain :loading="loadingLogs" @click="loadLogs">刷新日志</el-button>
              </ActionBar>
            </template>

            <el-table :data="logList" v-loading="loadingLogs" style="width: 100%">
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="user_id" label="用户 ID" width="100" />
              <el-table-column prop="operation" label="操作内容" min-width="280" />
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
            description="在这里维护系统账号和角色权限。"
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
                  <el-tag effect="plain" round>
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
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreateDialog" title="新增账号" width="420px">
      <el-form :model="createForm" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="createForm.password" type="password" show-password placeholder="请输入初始密码" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role">
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
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
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
import { formatDateTime } from '@/utils/formatters'
import {
  clearGalleryData,
  createNewUser,
  fetchAuditLogs,
  fetchSysConfig,
  fetchSystemStats,
  fetchUserList,
  rebuildGalleryData,
  removeUser,
  syncGalleryData,
  updateSysConfig
} from '@/api/admin'

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
  loading: modelLoading,
  applying,
  modelFiles,
  selectedModelFile,
  modelState,
  loadModelMeta,
  applySelectedModel
} = useModelMeta()

const menuItems = [
  { key: 'settings', index: '01', label: '系统设置', description: '运行设备、阈值和当前模型' },
  { key: 'gallery', index: '02', label: '图库处理', description: '处理新增图片或重做全部特征' },
  { key: 'monitor', index: '03', label: '运行监控', description: '查看图库规模与引擎状态' },
  { key: 'logs', index: '04', label: '操作日志', description: '查看登录和后台操作记录' },
  { key: 'users', index: '05', label: '账号权限', description: '管理用户与角色' }
]

const activeMenu = ref('settings')
const loadingConfig = ref(false)
const savingConfig = ref(false)
const loadingStats = ref(false)
const loadingLogs = ref(false)
const loadingUsers = ref(false)
const creatingUser = ref(false)
const showCreateDialog = ref(false)
const currentPage = ref(1)
const pageSize = 15
const totalLogs = ref(0)
const logList = ref([])
const userList = ref([])
const shownMismatchKey = ref('')

const sysConfig = reactive({
  model_device: 'cpu',
  similarity_threshold: 0.5,
  max_results: 50,
  log_level: 'INFO'
})

const sysStats = reactive({
  total_images: 0,
  total_vehicles: 0,
  latest_ingestion_time: '暂无记录'
})

const createForm = reactive({
  username: '',
  password: '',
  role: 'user'
})

const galleryMismatch = computed(
  () => Boolean(modelState.value.gallery) && !modelState.value.galleryMatchesCurrent
)
const galleryModelUnknown = computed(
  () => !modelState.value.gallery && Number(sysStats.total_images) > 0
)
const syncBlocked = computed(() => galleryMismatch.value || galleryModelUnknown.value)
const syncBlockedMessage = computed(() => {
  if (galleryMismatch.value) {
    return `当前模型为 ${modelState.value.current || '未记录'}，图库特征仍由 ${modelState.value.gallery || '未记录'} 计算，请先重新处理全部图片。`
  }

  return '当前图库已有特征数据，但没有记录它使用的模型。建议先重新处理全部图片一次。'
})

const loadConfig = async () => {
  loadingConfig.value = true

  try {
    const response = await fetchSysConfig()
    Object.assign(sysConfig, {
      model_device: response.data?.model_device || 'cpu',
      similarity_threshold: Number(response.data?.similarity_threshold ?? 0.5),
      max_results: Number(response.data?.max_results ?? 50),
      log_level: response.data?.log_level || 'INFO'
    })
    return response.data
  } finally {
    loadingConfig.value = false
  }
}

const loadStats = async () => {
  loadingStats.value = true

  try {
    const response = await fetchSystemStats()
    Object.assign(sysStats, {
      total_images: Number(response.data?.total_images ?? 0),
      total_vehicles: Number(response.data?.total_vehicles ?? 0),
      latest_ingestion_time: response.data?.latest_ingestion_time || '暂无记录'
    })
    return response.data
  } finally {
    loadingStats.value = false
  }
}

const loadLogs = async () => {
  loadingLogs.value = true

  try {
    const response = await fetchAuditLogs(currentPage.value, pageSize)
    logList.value = Array.isArray(response.data?.items) ? response.data.items : []
    totalLogs.value = Number(response.data?.total ?? 0)
  } finally {
    loadingLogs.value = false
  }
}

const loadUsers = async () => {
  loadingUsers.value = true

  try {
    const response = await fetchUserList()
    userList.value = Array.isArray(response.data) ? response.data : []
  } finally {
    loadingUsers.value = false
  }
}

const reloadModelMeta = async (options = {}) => {
  try {
    await loadModelMeta(options)
  } catch {
    // Request layer and inline banner handle the error.
  }
}

const maybeWarnMismatch = async (force = false) => {
  if (!galleryMismatch.value) {
    return
  }

  const key = `${modelState.value.current}::${modelState.value.gallery}`
  if (!force && shownMismatchKey.value === key) {
    return
  }

  shownMismatchKey.value = key
  await ElMessageBox.alert(
    `当前模型“${modelState.value.current}”与图库特征模型“${modelState.value.gallery}”不一致。请先重新处理全部图片，否则前台检索会被暂时停用。`,
    '模型与图库不一致',
    {
      confirmButtonText: '知道了',
      type: 'warning'
    }
  )
}

const initializePage = async () => {
  syncSession()

  await Promise.all([
    loadConfig(),
    loadStats(),
    loadLogs(),
    refreshStatus().catch(() => null),
    reloadModelMeta()
  ])

  await maybeWarnMismatch()
}

const handleMenuSelect = async (key) => {
  activeMenu.value = key

  if (key === 'logs') {
    await loadLogs()
  }

  if (key === 'users') {
    await loadUsers()
  }

  if (key === 'monitor') {
    await loadStats()
  }
}

const handlePageChange = async (page) => {
  currentPage.value = page
  await loadLogs()
}

const handleSaveConfig = async () => {
  savingConfig.value = true

  try {
    await updateSysConfig({ ...sysConfig })
    await Promise.all([loadConfig(), reloadModelMeta()])
    ElMessage.success('系统参数已保存。')
  } finally {
    savingConfig.value = false
  }
}

const handleApplyModel = async () => {
  try {
    await applySelectedModel()
    await loadStats()
    ElMessage.success('当前模型已更新。')
    await maybeWarnMismatch(true)
  } catch {
    // Request layer handles the error message.
  }
}

const handleSyncGallery = async () => {
  try {
    await syncGalleryData()
    startPolling()
    await refreshStatus().catch(() => null)
    ElMessage.success('已开始处理新增图片。')
  } catch {
    // Request layer handles the error message.
  }
}

const handleRebuildGallery = async () => {
  try {
    await ElMessageBox.confirm(
      '这会重新处理全部图片并覆盖现有图库特征，是否继续？',
      '重新处理全部图片',
      {
        confirmButtonText: '继续',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await rebuildGalleryData()
    startPolling()
    await refreshStatus().catch(() => null)
    ElMessage.success('已开始重新处理全部图片。')
  } catch (error) {
    if (error !== 'cancel') {
      // Request layer handles actual request failures.
    }
  }
}

const handleClearGallery = async () => {
  try {
    await ElMessageBox.confirm(
      '清空后将删除当前图库中的全部特征记录，是否继续？',
      '清空图库记录',
      {
        confirmButtonText: '继续',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await clearGalleryData()
    stopPolling()
    await Promise.all([loadStats(), refreshStatus().catch(() => null), reloadModelMeta()])
    ElMessage.success('图库记录已清空。')
  } catch (error) {
    if (error !== 'cancel') {
      // Request layer handles actual request failures.
    }
  }
}

const handleCreateUser = async () => {
  if (!createForm.username.trim() || !createForm.password.trim()) {
    ElMessage.warning('请先填写用户名和密码。')
    return
  }

  creatingUser.value = true

  try {
    await createNewUser({
      username: createForm.username.trim(),
      password: createForm.password,
      role: createForm.role
    })
    showCreateDialog.value = false
    createForm.username = ''
    createForm.password = ''
    createForm.role = 'user'
    await loadUsers()
    ElMessage.success('账号已创建。')
  } finally {
    creatingUser.value = false
  }
}

const handleDeleteUser = async (userId) => {
  try {
    await ElMessageBox.confirm('删除后该账号将无法继续登录，是否继续？', '删除账号', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await removeUser(userId)
    await loadUsers()
    ElMessage.success('账号已删除。')
  } catch (error) {
    if (error !== 'cancel') {
      // Request layer handles actual request failures.
    }
  }
}

const handleLogout = async () => {
  await logoutAndRedirect()
  ElMessage.success('已退出登录。')
}

onMounted(() => {
  initializePage().catch(() => {})
})
</script>

<style scoped>
.header-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: flex-end;
}

.admin-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.admin-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.settings-panel {
  padding: 22px;
  border: 1px solid var(--border-soft);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.52);
  box-shadow: var(--shadow-ring);
}

.settings-copy h3 {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 30px;
  font-weight: 500;
}

.settings-copy p {
  margin: 10px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.settings-form {
  margin-top: 18px;
}

.model-state-grid,
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
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
  margin-top: 18px;
}

@media (max-width: 1180px) {
  .admin-layout,
  .settings-grid,
  .model-state-grid,
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
