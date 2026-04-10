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

                  <div class="settings-inline-grid">
                    <el-form-item label="最大返回结果数">
                      <el-input-number v-model="sysConfig.max_results" :min="1" :max="500" />
                    </el-form-item>

                    <el-form-item label="默认返回结果数">
                      <el-input-number v-model="sysConfig.search_default_top_k" :min="1" :max="sysConfig.max_results" />
                    </el-form-item>
                  </div>

                  <div class="settings-inline-grid">
                    <el-form-item label="图库轮询间隔 (ms)">
                      <el-input-number v-model="sysConfig.gallery_poll_interval_ms" :min="500" :max="60000" :step="100" />
                    </el-form-item>

                    <el-form-item label="当前模型已加载">
                      <el-input :model-value="modelState.initialized ? '是' : '否'" disabled />
                    </el-form-item>
                  </div>

                  <el-form-item label="允许查询图片格式">
                    <el-input
                      v-model="sysConfig.allowed_query_suffixes_text"
                      placeholder="例如 .jpg, .jpeg, .png, .bmp, .webp"
                    />
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
                  <el-button plain :loading="modelLoading" @click="reloadModelState">刷新模型列表</el-button>
                  <el-button
                    type="primary"
                    :loading="applying"
                    :disabled="!selectedModelFile || selectedModelFile === modelState.current"
                    @click="handleApplyModel"
                  >
                    应用当前模型
                  </el-button>
                </ActionBar>

                <div class="top-gap runtime-info-grid">
                  <div v-for="item in runtimeInfoItems" :key="item.label" class="runtime-info-item">
                    <span>{{ item.label }}</span>
                    <strong :title="item.value">{{ item.value }}</strong>
                  </div>
                </div>
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

            <div class="gallery-path-card">
              <div class="gallery-path-copy">
                <strong>当前图库目录</strong>
                <code>{{ galleryPath }}</code>
              </div>

              <ActionBar align="right">
                <el-button plain @click="handleCopyGalleryPath">复制路径</el-button>
                <el-button plain @click="handleOpenGalleryFolder">打开文件夹</el-button>
              </ActionBar>
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
            description="把图库规模、模型状态、任务状态与账号日志规模整理成运维视角的总览卡片。"
          >
            <template #actions>
              <ActionBar align="right">
                <el-button plain :loading="loadingOverview" @click="loadOverview">刷新总览</el-button>
              </ActionBar>
            </template>

            <div class="overview-grid">
              <StatCard
                v-for="item in overviewCards"
                :key="item.label"
                :label="item.label"
                :value="item.value"
                :hint="item.hint"
                :mono="item.mono"
              />
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
              <el-table-column label="属性" width="140">
                <template #default="scope">
                  <el-tag v-if="scope.row.is_builtin" effect="plain" type="warning" round>内置账号</el-tag>
                  <span v-else class="muted-inline">自定义账号</span>
                </template>
              </el-table-column>
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
              <el-table-column label="操作" width="100" align="center">
                <template #default="scope">
                  <el-button size="small" plain @click="openEditDialog(scope.row)">编辑</el-button>
                </template>
              </el-table-column>
            </el-table>
          </SectionCard>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreateDialog" title="新增账号" width="440px">
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

    <el-dialog v-model="showEditDialog" title="编辑账号" width="480px">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="editForm.password" type="password" show-password placeholder="留空表示不修改密码" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" :disabled="editingBuiltin">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>

      <div v-if="editingBuiltin" class="dialog-note">
        <strong>内置账号保护</strong>
        <p>内置账号允许改名和改密码，但不能删除，也不能降级为普通用户。</p>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <ActionBar align="left">
            <el-button
              plain
              type="danger"
              :disabled="editingBuiltin || savingUser"
              @click="handleDeleteUser(editingUser)"
            >
              删除账号
            </el-button>
          </ActionBar>

          <ActionBar align="right">
            <el-button plain @click="showEditDialog = false">取消</el-button>
            <el-button type="primary" :loading="savingUser" @click="handleSaveUser">保存修改</el-button>
          </ActionBar>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ActionBar from '@/components/base/action-bar.vue'
import PageHeader from '@/components/base/page-header.vue'
import SectionCard from '@/components/base/section-card.vue'
import StatCard from '@/components/base/stat-card.vue'
import StatusBanner from '@/components/base/status-banner.vue'
import AdminNav from '@/components/admin/admin-nav.vue'
import TerminalLogPanel from '@/components/admin/terminal-log-panel.vue'
import { useGalleryPolling } from '@/composables/use-gallery-polling'
import { useModelState } from '@/composables/use-model-state'
import { useSession } from '@/composables/use-session'
import { formatDateTime } from '@/utils/formatters'
import {
  clearGalleryRecords,
  createUser,
  deleteUser,
  fetchAdminOverview,
  fetchAuditLogs,
  fetchSystemConfig,
  fetchUsers,
  openGalleryFolder,
  rebuildGalleryRecords,
  saveSystemConfig,
  startGallerySync,
  updateUser
} from '@/api/admin'

const router = useRouter()
const { syncSession, logoutAndRedirect } = useSession(router)
const {
  isRunning,
  logs,
  errorMessage: galleryErrorMessage,
  refreshStatus,
  startPolling,
  stopPolling,
  setPollInterval
} = useGalleryPolling()
const {
  loading: modelLoading,
  applying,
  modelFiles,
  selectedModelFile,
  modelState,
  loadModelState,
  applySelectedModel
} = useModelState()

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
const loadingOverview = ref(false)
const loadingLogs = ref(false)
const loadingUsers = ref(false)
const creatingUser = ref(false)
const savingUser = ref(false)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingUser = ref(null)
const currentPage = ref(1)
const pageSize = 15
const totalLogs = ref(0)
const logList = ref([])
const userList = ref([])

const sysConfig = reactive({
  model_device: 'cpu',
  similarity_threshold: 0.5,
  max_results: 50,
  search_default_top_k: 10,
  gallery_poll_interval_ms: 1500,
  allowed_query_suffixes_text: '.jpg, .jpeg, .png, .bmp, .webp',
  log_level: 'INFO',
  gallery_dir: '',
  search_upload_dir: ''
})

const overview = reactive({
  total_images: 0,
  total_vehicles: 0,
  latest_ingestion_time: '暂无记录',
  current_model_file: '',
  gallery_model_file: '',
  gallery_model_matches_current: true,
  gallery_model_known: false,
  available_model_count: 0,
  model_device: 'cpu',
  initialized: false,
  gallery_task_running: false,
  gallery_task_state: 'idle',
  total_users: 0,
  total_logs: 0,
  latest_log_time: '暂无记录',
  gallery_dir: '',
  search_upload_dir: ''
})

const createForm = reactive({
  username: '',
  password: '',
  role: 'user'
})

const editForm = reactive({
  id: null,
  username: '',
  password: '',
  role: 'user'
})

const galleryMismatch = computed(
  () => Boolean(modelState.value.galleryModelKnown) && !modelState.value.galleryMatchesCurrent
)
const galleryModelUnknown = computed(
  () => modelState.value.galleryHasRecords && !modelState.value.galleryModelKnown
)
const syncBlocked = computed(() => galleryMismatch.value || galleryModelUnknown.value)
const syncBlockedMessage = computed(() => {
  if (galleryMismatch.value) {
    return `当前模型为 ${modelState.value.current || '未记录'}，图库特征仍由 ${modelState.value.gallery || '未记录'} 计算，请先重新处理全部图片。`
  }

  return '当前图库已有特征数据，但没有记录它使用的模型。建议先重新处理全部图片一次。'
})
const galleryPath = computed(() => sysConfig.gallery_dir || overview.gallery_dir || '未配置')
const editingBuiltin = computed(() => Boolean(editingUser.value?.is_builtin))
const runtimeInfoItems = computed(() => ([
  { label: '图库目录', value: galleryPath.value },
  { label: '查询上传目录', value: sysConfig.search_upload_dir || overview.search_upload_dir || '未配置' },
  { label: '允许查询格式', value: sysConfig.allowed_query_suffixes_text || '未配置' },
  { label: '图库任务轮询', value: `${sysConfig.gallery_poll_interval_ms} ms` }
]))
const overviewCards = computed(() => ([
  { label: '图库图片总数', value: String(overview.total_images), hint: '当前已入库特征记录数' },
  { label: '唯一车辆 ID', value: String(overview.total_vehicles), hint: '按 vehicle_id 去重' },
  { label: '最近入库时间', value: overview.latest_ingestion_time, hint: '最近一次写入图库记录的时间' },
  { label: '当前模型', value: modelState.value.current || overview.current_model_file || '未记录', hint: '前后台当前使用的模型', mono: true },
  { label: '图库特征模型', value: modelState.value.gallery || overview.gallery_model_file || '尚未记录', hint: '当前图库特征来源模型', mono: true },
  { label: '模型一致性', value: galleryMismatch.value ? '不一致' : (galleryModelUnknown.value ? '未记录' : '一致'), hint: '决定前台是否允许检索' },
  { label: '可用模型数', value: String(modelState.value.availableModelCount || overview.available_model_count), hint: 'outputs 中可用模型文件数量' },
  { label: '运行设备', value: modelState.value.device || overview.model_device || '未知', hint: '当前推理设备' },
  { label: '引擎状态', value: modelState.value.initialized ? '已初始化' : '未初始化', hint: 'ReID 引擎当前状态' },
  { label: '图库任务状态', value: isRunning.value ? '运行中' : '空闲', hint: '后台图库处理任务状态' },
  { label: '账号总数', value: String(overview.total_users), hint: '系统用户数量' },
  { label: '日志总数', value: String(overview.total_logs), hint: '审计日志累计数量' },
  { label: '最近日志时间', value: overview.latest_log_time, hint: '最近一条操作日志时间' },
  { label: '图库目录', value: galleryPath.value, hint: '当前扫描目录', mono: true }
]))

const parseSuffixes = (value) => {
  const suffixes = String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

  return suffixes.length ? suffixes : ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
}

const loadConfig = async () => {
  loadingConfig.value = true

  try {
    const response = await fetchSystemConfig()
    Object.assign(sysConfig, {
      model_device: response.data?.model_device || 'cpu',
      similarity_threshold: Number(response.data?.similarity_threshold ?? 0.5),
      max_results: Number(response.data?.max_results ?? 50),
      search_default_top_k: Number(response.data?.search_default_top_k ?? 10),
      gallery_poll_interval_ms: Number(response.data?.gallery_poll_interval_ms ?? 1500),
      allowed_query_suffixes_text: Array.isArray(response.data?.allowed_query_suffixes)
        ? response.data.allowed_query_suffixes.join(', ')
        : '.jpg, .jpeg, .png, .bmp, .webp',
      log_level: response.data?.log_level || 'INFO',
      gallery_dir: response.data?.gallery_dir || '',
      search_upload_dir: response.data?.search_upload_dir || ''
    })
    setPollInterval(sysConfig.gallery_poll_interval_ms)
    return response.data
  } finally {
    loadingConfig.value = false
  }
}

const loadOverview = async () => {
  loadingOverview.value = true

  try {
    const response = await fetchAdminOverview()
    Object.assign(overview, {
      total_images: Number(response.data?.total_images ?? 0),
      total_vehicles: Number(response.data?.total_vehicles ?? 0),
      latest_ingestion_time: response.data?.latest_ingestion_time || '暂无记录',
      current_model_file: response.data?.current_model_file || '',
      gallery_model_file: response.data?.gallery_model_file || '',
      gallery_model_matches_current: Boolean(response.data?.gallery_model_matches_current),
      gallery_model_known: Boolean(response.data?.gallery_model_known),
      available_model_count: Number(response.data?.available_model_count ?? 0),
      model_device: response.data?.model_device || 'cpu',
      initialized: Boolean(response.data?.initialized),
      gallery_task_running: Boolean(response.data?.gallery_task_running),
      gallery_task_state: response.data?.gallery_task_state || 'idle',
      total_users: Number(response.data?.total_users ?? 0),
      total_logs: Number(response.data?.total_logs ?? 0),
      latest_log_time: response.data?.latest_log_time || '暂无记录',
      gallery_dir: response.data?.gallery_dir || '',
      search_upload_dir: response.data?.search_upload_dir || ''
    })
    return response.data
  } finally {
    loadingOverview.value = false
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
    const response = await fetchUsers()
    userList.value = Array.isArray(response.data) ? response.data : []
  } finally {
    loadingUsers.value = false
  }
}

const reloadModelState = async (options = {}) => {
  try {
    await loadModelState(options)
  } catch {
    // Request layer and inline banner handle the error.
  }
}

const initializePage = async () => {
  syncSession()

  await Promise.all([
    loadConfig(),
    loadOverview(),
    loadLogs(),
    refreshStatus().catch(() => null),
    reloadModelState()
  ])
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
    await loadOverview()
  }
}

const handlePageChange = async (page) => {
  currentPage.value = page
  await loadLogs()
}

const handleSaveConfig = async () => {
  savingConfig.value = true

  try {
    await saveSystemConfig({
      model_device: sysConfig.model_device,
      similarity_threshold: Number(sysConfig.similarity_threshold),
      max_results: Number(sysConfig.max_results),
      search_default_top_k: Number(sysConfig.search_default_top_k),
      gallery_poll_interval_ms: Number(sysConfig.gallery_poll_interval_ms),
      allowed_query_suffixes: parseSuffixes(sysConfig.allowed_query_suffixes_text),
      log_level: sysConfig.log_level
    })
    await Promise.all([loadConfig(), loadOverview(), reloadModelState()])
    ElMessage.success('系统参数已保存。')
  } finally {
    savingConfig.value = false
  }
}

const handleApplyModel = async () => {
  try {
    await applySelectedModel()
    await Promise.all([loadOverview(), loadConfig()])
    ElMessage.success('当前模型已更新。')
  } catch {
    // Request layer handles the error message.
  }
}

const handleSyncGallery = async () => {
  try {
    await startGallerySync()
    startPolling()
    await Promise.all([refreshStatus().catch(() => null), loadOverview()])
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

    await rebuildGalleryRecords()
    startPolling()
    await Promise.all([refreshStatus().catch(() => null), loadOverview()])
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

    await clearGalleryRecords()
    stopPolling()
    await Promise.all([
      loadOverview(),
      loadConfig(),
      refreshStatus().catch(() => null),
      reloadModelState()
    ])
    ElMessage.success('图库记录已清空。')
  } catch (error) {
    if (error !== 'cancel') {
      // Request layer handles actual request failures.
    }
  }
}

const handleCopyGalleryPath = async () => {
  try {
    await navigator.clipboard.writeText(galleryPath.value)
    ElMessage.success('图库路径已复制。')
  } catch {
    ElMessage.warning('当前环境不支持自动复制，请手动复制路径。')
  }
}

const handleOpenGalleryFolder = async () => {
  try {
    const response = await openGalleryFolder()
    if (response.data?.opened) {
      ElMessage.success('已尝试打开图库目录。')
    } else {
      ElMessage.warning(response.message || '当前环境不支持自动打开图库目录，请直接使用路径。')
    }
  } catch {
    // Request layer handles the error message.
  }
}

const resetCreateForm = () => {
  createForm.username = ''
  createForm.password = ''
  createForm.role = 'user'
}

const handleCreateUser = async () => {
  if (!createForm.username.trim() || !createForm.password.trim()) {
    ElMessage.warning('请先填写用户名和密码。')
    return
  }

  creatingUser.value = true

  try {
    await createUser({
      username: createForm.username.trim(),
      password: createForm.password,
      role: createForm.role
    })
    showCreateDialog.value = false
    resetCreateForm()
    await Promise.all([loadUsers(), loadOverview()])
    ElMessage.success('账号已创建。')
  } finally {
    creatingUser.value = false
  }
}

const openEditDialog = (user) => {
  editingUser.value = user
  editForm.id = user.id
  editForm.username = user.username
  editForm.password = ''
  editForm.role = user.role
  showEditDialog.value = true
}

const handleSaveUser = async () => {
  if (!editForm.id || !editForm.username.trim()) {
    ElMessage.warning('请先填写用户名。')
    return
  }

  savingUser.value = true

  try {
    const payload = {
      username: editForm.username.trim(),
      role: editForm.role
    }

    if (editForm.password.trim()) {
      payload.password = editForm.password
    }

    await updateUser(editForm.id, payload)
    showEditDialog.value = false
    editingUser.value = null
    await Promise.all([loadUsers(), loadOverview()])
    ElMessage.success('账号信息已更新。')
  } finally {
    savingUser.value = false
  }
}

const handleDeleteUser = async (user) => {
  if (!user?.id) {
    return
  }

  try {
    await ElMessageBox.confirm('删除后该账号将无法继续登录，是否继续？', '删除账号', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteUser(user.id)
    showEditDialog.value = false
    editingUser.value = null
    await Promise.all([loadUsers(), loadOverview()])
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

.settings-inline-grid,
.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.model-state-grid,
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.overview-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.runtime-info-grid {
  display: grid;
  gap: 12px;
}

.runtime-info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border: 1px solid var(--border-soft);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.42);
}

.runtime-info-item span {
  color: var(--text-muted);
  font-size: 12px;
}

.runtime-info-item strong {
  color: var(--text-primary);
  font-size: 14px;
  overflow-wrap: anywhere;
}

.gallery-path-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.48);
}

.gallery-path-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.gallery-path-copy strong {
  color: var(--text-primary);
  font-size: 15px;
}

.gallery-path-copy code {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 13px;
  overflow-wrap: anywhere;
}

.compact-grid {
  margin-bottom: 18px;
}

.top-gap {
  margin-top: 18px;
}

.muted-inline {
  color: var(--text-muted);
  font-size: 13px;
}

.dialog-note {
  margin-top: 8px;
  padding: 14px 16px;
  border: 1px solid var(--border-soft);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.44);
}

.dialog-note strong {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
}

.dialog-note p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.55;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

@media (max-width: 1280px) {
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1180px) {
  .admin-layout,
  .settings-grid,
  .overview-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .settings-inline-grid,
  .model-state-grid,
  .stats-grid,
  .overview-grid {
    grid-template-columns: 1fr;
  }

  .dialog-footer,
  .gallery-path-card {
    flex-direction: column;
    align-items: stretch;
  }

  .header-meta {
    justify-content: flex-start;
  }
}
</style>
