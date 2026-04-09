<template>
  <el-container class="admin-layout">
    <el-aside :width="isCollapse ? '80px' : '260px'" class="sidebar-container">
      <div class="brand-header">
        <span v-show="!isCollapse" class="brand-text">视觉计算终端</span>
        <div class="collapse-trigger" @click="toggleCollapse">
          <el-icon><Fold v-if="!isCollapse" /><Expand v-else /></el-icon>
        </div>
      </div>
      <div class="menu-scroll-area">
        <el-menu
          :default-active="activeMenu"
          class="macos-menu"
          :collapse="isCollapse"
          @select="handleMenuSelect"
          background-color="transparent"
          text-color="#ebebf5"
          active-text-color="#ffffff"
        >
          <el-menu-item index="logs">
            <el-icon><Document /></el-icon>
            <template #title>系统审计日志</template>
          </el-menu-item>
          <el-menu-item index="users">
            <el-icon><User /></el-icon>
            <template #title>账户权限管理</template>
          </el-menu-item>
          <el-menu-item index="gallery">
            <el-icon><Files /></el-icon>
            <template #title>特征底库调度</template>
          </el-menu-item>
          <el-menu-item index="monitor">
            <el-icon><Monitor /></el-icon>
            <template #title>运行状态监控</template>
          </el-menu-item>
          <el-menu-item index="settings">
            <el-icon><Setting /></el-icon>
            <template #title>系统参数配置</template>
          </el-menu-item>
        </el-menu>
      </div>
    </el-aside>

    <el-container class="main-wrapper">
      <el-header class="top-header">
        <div class="header-title">{{ currentMenuTitle }}</div>
        <el-button color="#ff453a" size="small" @click="handleLogout" class="apple-btn">安全退出</el-button>
      </el-header>

      <el-main class="content-body">
        <div v-if="activeMenu === 'logs'" class="module-container">
          <el-table :data="logList" v-loading="loadingLogs" style="width: 100%">
            <el-table-column prop="id" label="标识" width="80" />
            <el-table-column prop="user_id" label="实体主键" width="100" />
            <el-table-column prop="operation" label="行为简述" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status ? 'success' : 'danger'" effect="dark" round>
                  {{ scope.row.status ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="exec_time" label="发生时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.exec_time) }}
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper">
            <el-pagination
              layout="prev, pager, next"
              :total="totalLogs"
              :page-size="pageSize"
              v-model:current-page="currentPage"
              @current-change="handlePageChange"
            />
          </div>
        </div>

        <div v-if="activeMenu === 'users'" class="module-container">
          <div class="action-bar">
            <el-button type="primary" @click="showCreateDialog = true" class="apple-btn">新增账户实体</el-button>
          </div>
          <el-table :data="userList" v-loading="loadingUsers" style="width: 100%; margin-top: 15px;">
            <el-table-column prop="id" label="主键" width="80" />
            <el-table-column prop="username" label="登录账号" />
            <el-table-column prop="role" label="权限角色" width="150">
              <template #default="scope">
                <el-tag :type="scope.row.role === 'admin' ? 'warning' : 'info'" effect="dark" round>
                  {{ scope.row.role === 'admin' ? '管理员' : '操作员' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="创建时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.create_time) }}
              </template>
            </el-table-column>
            <el-table-column label="操作指令" width="120">
              <template #default="scope">
                <el-button color="#ff453a" size="small" @click="handleDeleteUser(scope.row.id)" :disabled="scope.row.id === 1" class="apple-btn" plain>
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="activeMenu === 'gallery'" class="module-container">
          <div class="action-bar">
            <el-button type="primary" :disabled="isEngineRunning" @click="handleSyncGallery" class="apple-btn">增量特征同步</el-button>
            <el-button color="#ffd60a" style="color: #000;" :disabled="isEngineRunning" @click="handleRebuildGallery" class="apple-btn">全量底库重建</el-button>
            <el-button color="#ff453a" :disabled="isEngineRunning" @click="handleClearGallery" class="apple-btn">彻底清空底库</el-button>
          </div>
          
          <div class="macos-terminal">
            <div class="terminal-header">
              <div class="traffic-lights">
                <span class="light red"></span>
                <span class="light yellow"></span>
                <span class="light green"></span>
              </div>
              <div class="terminal-title">计算引擎进程</div>
            </div>
            <div class="terminal-body" ref="terminalRef">
              <div v-for="(log, index) in engineLogs" :key="index" class="terminal-line">
                {{ log }}
              </div>
              <div v-if="isEngineRunning" class="terminal-cursor">_</div>
            </div>
          </div>
        </div>

        <div v-if="activeMenu === 'monitor'" class="module-container transparent-container">
          <div class="action-bar">
            <el-button type="primary" @click="loadStats" :loading="loadingStats" class="apple-btn">刷新统计数据</el-button>
          </div>
          <el-row :gutter="24" style="margin-top: 20px;">
            <el-col :span="8">
              <el-card shadow="never" class="apple-stat-card" v-loading="loadingStats">
                <div class="stat-title">底库特征总规模</div>
                <div class="stat-value">{{ sysStats.total_images }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never" class="apple-stat-card" v-loading="loadingStats">
                <div class="stat-title">唯一车辆身份数</div>
                <div class="stat-value">{{ sysStats.total_vehicles }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never" class="apple-stat-card" v-loading="loadingStats">
                <div class="stat-title">最新入库时间</div>
                <div class="stat-value text-small">{{ sysStats.latest_ingestion_time }}</div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <div v-if="activeMenu === 'settings'" class="module-container transparent-container">
          <el-card shadow="never" class="apple-config-card" v-loading="loadingConfig">
            <el-form :model="sysConfig" label-width="140px" label-position="left">
              <el-form-item label="计算引擎设备">
                <el-select v-model="sysConfig.model_device" style="width: 100%;">
                  <el-option label="中央处理器 (CPU)" value="cpu" />
                  <el-option label="图形处理器 (CUDA)" value="cuda" />
                </el-select>
              </el-form-item>
              <el-form-item label="核心日志级别">
                <el-select v-model="sysConfig.log_level" style="width: 100%;">
                  <el-option label="调试" value="DEBUG" />
                  <el-option label="信息" value="INFO" />
                  <el-option label="警告" value="WARNING" />
                  <el-option label="错误" value="ERROR" />
                </el-select>
              </el-form-item>
              <el-form-item label="相似度截断阈值">
                <el-slider v-model="sysConfig.similarity_threshold" :min="0" :max="1" :step="0.01" show-input />
              </el-form-item>
              <el-form-item label="全局返回上限">
                <el-input-number v-model="sysConfig.max_results" :min="10" :max="500" />
              </el-form-item>
              <el-form-item style="margin-top: 30px;">
                <el-button type="primary" @click="handleSaveConfig" :loading="savingConfig" class="apple-btn">执行系统参数覆写</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-main>
    </el-container>

    <el-dialog v-model="showCreateDialog" title="创建新账户实体" width="380px" custom-class="apple-dialog" :show-close="false">
      <el-form :model="newUserForm" label-width="80px" label-position="top">
        <el-form-item label="登录账号">
          <el-input v-model="newUserForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="newUserForm.password" type="password" show-password autocomplete="off" />
        </el-form-item>
        <el-form-item label="分配角色">
          <el-select v-model="newUserForm.role" style="width: 100%">
            <el-option label="普通操作员" value="user" />
            <el-option label="系统管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer-apple">
          <el-button @click="showCreateDialog = false" text bg>取消</el-button>
          <el-button type="primary" @click="handleCreateUser" :loading="creatingUser" class="apple-btn">确认构建</el-button>
        </div>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAuditLogs, syncGalleryData, clearGalleryData, rebuildGalleryData, fetchGalleryStatus, fetchUserList, createNewUser, removeUser, fetchSystemStats, fetchSysConfig, updateSysConfig, fetchModelFiles, selectModelFile } from '@/api/admin'
import { logout } from '@/api/auth'

const router = useRouter()
const isCollapse = ref(false)
const activeMenu = ref('logs')

const menuTitles = {
  logs: '系统审计日志',
  users: '账户权限管理',
  gallery: '特征底库调度',
  monitor: '运行状态监控',
  settings: '系统参数配置'
}
const currentMenuTitle = computed(() => menuTitles[activeMenu.value])

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
  log_level: 'INFO',
  current_model_file: ''
})
const modelFiles = ref([])

const isEngineRunning = ref(false)
const engineLogs = ref([])
const terminalRef = ref(null)
let pollTimer = null

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const handleMenuSelect = (index) => {
  activeMenu.value = index
  if (index === 'gallery') {
    pollEngineStatus()
    if (isEngineRunning.value) startPolling()
  } else {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }
  if (index === 'monitor') loadStats()
  if (index === 'settings') loadConfig()
}

const loadLogs = async () => {
  loadingLogs.value = true
  try {
    const response = await fetchAuditLogs(currentPage.value, pageSize.value)
    logList.value = response.data.items
    totalLogs.value = response.data.total
  } catch (error) {
  } finally {
    loadingLogs.value = false
  }
}

const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const response = await fetchUserList()
    userList.value = response.data
  } catch (error) {
  } finally {
    loadingUsers.value = false
  }
}

const loadStats = async () => {
  loadingStats.value = true
  try {
    const res = await fetchSystemStats()
    sysStats.total_images = res.data.total_images
    sysStats.total_vehicles = res.data.total_vehicles
    sysStats.latest_ingestion_time = res.data.latest_ingestion_time
  } catch (error) {
  } finally {
    loadingStats.value = false
  }
}

const loadConfig = async () => {
  loadingConfig.value = true
  try {
    const res = await fetchSysConfig()
    Object.assign(sysConfig, res.data)
  } catch (error) {
  } finally {
    loadingConfig.value = false
  }
}

const handleSaveConfig = async () => {
  savingConfig.value = true
  try {
    await updateSysConfig(sysConfig)
    ElMessage.success('系统底层参数覆写成功')
  } catch (error) {
  } finally {
    savingConfig.value = false
  }
}

const pollEngineStatus = async () => {
  try {
    const res = await fetchGalleryStatus()
    isEngineRunning.value = res.data.is_running
    engineLogs.value = res.data.logs
    nextTick(() => {
      if (terminalRef.value) {
        terminalRef.value.scrollTop = terminalRef.value.scrollHeight
      }
    })
    if (!isEngineRunning.value && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  } catch (error) {
  }
}

const startPolling = () => {
  if (!pollTimer) {
    pollTimer = setInterval(pollEngineStatus, 1500)
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadLogs()
}

const handleSyncGallery = async () => {
  try {
    await syncGalleryData()
    ElMessage.success('增量底库同步管线已拉起')
    startPolling()
  } catch (error) {
  }
}

const handleRebuildGallery = async () => {
  try {
    await ElMessageBox.confirm('全量重建将抛弃现有特征矩阵并重新耗时运算，是否继续执行指令', '系统验证', {
      confirmButtonText: '确认执行',
      cancelButtonText: '终止操作',
      type: 'warning'
    })
    await rebuildGalleryData()
    ElMessage.success('全量重建管线已拉起')
    startPolling()
  } catch (error) {
  }
}

const handleClearGallery = async () => {
  try {
    await ElMessageBox.confirm('该动作将对数据库进行物理截断且不可逆，确认要抹除所有视觉特征数据吗', '高危操作警告', {
      confirmButtonText: '强制销毁',
      cancelButtonText: '撤销',
      type: 'error'
    })
    await clearGalleryData()
    ElMessage.success('底层特征表已完全抹除')
    pollEngineStatus()
  } catch (error) {
  }
}

const handleCreateUser = async () => {
  if (!newUserForm.username || !newUserForm.password) {
    ElMessage.warning('账号与密码向量不可为空')
    return
  }
  creatingUser.value = true
  try {
    await createNewUser(newUserForm)
    ElMessage.success('账户实体构建成功')
    showCreateDialog.value = false
    newUserForm.username = ''
    newUserForm.password = ''
    newUserForm.role = 'user'
    loadUsers()
  } catch (error) {
  } finally {
    creatingUser.value = false
  }
}

const handleDeleteUser = async (id) => {
  try {
    await ElMessageBox.confirm('确认物理销毁该账户实体', '系统警告', {
      confirmButtonText: '执行移除',
      cancelButtonText: '放弃操作',
      type: 'warning'
    })
    await removeUser(id)
    ElMessage.success('账户实体已销毁')
    loadUsers()
  } catch (error) {
  }
}

const handleLogout = async () => {
  try {
    await logout()
  } catch (error) {
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    router.push('/login')
  }
}

const formatTime = (timeStr) => {
  if (!timeStr) return '未知'
  return timeStr.replace('T', ' ').substring(0, 19)
}

onMounted(() => {
  document.documentElement.classList.add('dark')
  loadLogs()
  loadUsers()
})

onBeforeUnmount(() => {
  document.documentElement.classList.remove('dark')
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.admin-layout {
  height: 100vh;
  padding: 16px;
  gap: 16px;
  background-color: transparent;
}

.sidebar-container {
  background: rgba(30, 30, 30, 0.4);
  backdrop-filter: blur(40px) saturate(200%);
  -webkit-backdrop-filter: blur(40px) saturate(200%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  overflow: hidden;
}

.brand-header {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  font-weight: 600;
  font-size: 16px;
  color: #ffffff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.collapse-trigger {
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  transition: background 0.2s;
}

.collapse-trigger:hover {
  background: rgba(255, 255, 255, 0.1);
}

.menu-scroll-area {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
}

.macos-menu {
  border-right: none;
}

.macos-menu .el-menu-item {
  border-radius: 12px;
  margin-bottom: 4px;
  height: 44px;
  line-height: 44px;
}

.macos-menu .el-menu-item.is-active {
  background: var(--el-color-primary) !important;
  color: #ffffff !important;
  box-shadow: 0 4px 12px rgba(10, 132, 255, 0.3);
}

.macos-menu .el-menu-item:hover:not(.is-active) {
  background: rgba(255, 255, 255, 0.08) !important;
}

.main-wrapper {
  background: transparent;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
}

.top-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  margin-bottom: 16px;
}

.header-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: #ffffff;
}

.content-body {
  padding: 0;
  overflow-y: auto;
}

.module-container {
  background: rgba(30, 30, 30, 0.5);
  backdrop-filter: blur(40px) saturate(200%);
  -webkit-backdrop-filter: blur(40px) saturate(200%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 24px;
  min-height: calc(100vh - 124px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.transparent-container {
  background: transparent;
  border: none;
  backdrop-filter: none;
  box-shadow: none;
  padding: 0;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.apple-stat-card {
  height: 140px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -1px;
}

.text-small {
  font-size: 24px;
}

.apple-config-card {
  max-width: 640px;
  padding: 10px;
}

.macos-terminal {
  margin-top: 24px;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.terminal-header {
  height: 38px;
  background: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  padding: 0 16px;
  position: relative;
}

.traffic-lights {
  display: flex;
  gap: 8px;
}

.light {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.light.red { background: #ff5f56; }
.light.yellow { background: #ffbd2e; }
.light.green { background: #27c93f; }

.terminal-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-size: 13px;
  font-weight: 500;
  color: #8e8e93;
}

.terminal-body {
  height: 400px;
  overflow-y: auto;
  padding: 16px;
  font-family: "SF Mono", Consolas, Menlo, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #32d74b;
}

.terminal-cursor {
  display: inline-block;
  animation: blink 1s step-end infinite;
  color: #32d74b;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.dialog-footer-apple {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
