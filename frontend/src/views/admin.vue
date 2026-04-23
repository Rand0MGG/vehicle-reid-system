<template>
  <div class="app-page">
    <div class="app-shell">
      <PageHeader
        eyebrow="Admin Console"
        title="后台控制台"
        description="系统设置只管理系统参数；模型配置独立维护模型档案、发布状态和每个模型的图库特征。"
      >
        <template #meta>
          <div class="header-meta">
            <span class="app-chip">图库图片 <strong>{{ overview.total_images }}</strong></span>
            <span class="app-chip">模型档案 <strong>{{ modelProfiles.length }}</strong></span>
          </div>
        </template>
        <template #actions>
          <el-button plain @click="router.push('/search')">返回前台</el-button>
          <el-button @click="handleLogout">退出登录</el-button>
        </template>
      </PageHeader>

      <div class="admin-layout">
        <AdminNav :items="menuItems" :active-key="activeMenu" @select="handleMenuSelect" />

        <main class="admin-content">
          <SectionCard
            v-if="activeMenu === 'settings'"
            eyebrow="Settings"
            title="系统设置"
            description="这里只维护设备、阈值、返回数量、文件浏览根目录等系统参数。"
          >
            <el-form :model="sysConfig" label-position="top" class="settings-form">
              <div class="settings-inline-grid">
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
              </div>

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
                <el-form-item label="深度思考图库上限">
                  <el-input-number v-model="sysConfig.max_deep_thinking_gallery_size" :min="1" :max="50000" />
                </el-form-item>
                <el-form-item label="深度思考候选下限">
                  <el-input-number v-model="sysConfig.deep_thinking_candidate_limit_min" :min="1" :max="sysConfig.deep_thinking_candidate_limit_max" />
                </el-form-item>
              </div>

              <div class="settings-inline-grid">
                <el-form-item label="深度思考候选上限">
                  <el-input-number v-model="sysConfig.deep_thinking_candidate_limit_max" :min="sysConfig.deep_thinking_candidate_limit_min" :max="5000" />
                </el-form-item>
                <el-form-item label="图库任务轮询间隔 (ms)">
                  <el-input-number v-model="sysConfig.gallery_poll_interval_ms" :min="500" :max="60000" :step="100" />
                </el-form-item>
              </div>

              <el-form-item label="允许查询图片格式">
                <el-input v-model="sysConfig.allowed_query_suffixes_text" placeholder=".jpg, .jpeg, .png, .bmp, .webp" />
              </el-form-item>

              <el-form-item label="文件浏览器根目录">
                <el-input
                  v-model="sysConfig.file_browser_roots_text"
                  type="textarea"
                  :rows="3"
                  placeholder="每行一个允许浏览的目录，用于选择图库图片。"
                />
              </el-form-item>
            </el-form>

            <ActionBar>
              <el-button type="primary" :loading="savingConfig" @click="handleSaveConfig">保存系统参数</el-button>
              <el-button plain :loading="loadingConfig" @click="loadConfig">重新读取</el-button>
            </ActionBar>
          </SectionCard>

          <SectionCard
            v-if="activeMenu === 'gallery'"
            eyebrow="Gallery"
            title="图库图片"
            description="先把图片路径注册到数据库；这一步不区分模型，也不会提取特征。"
          >
            <template #actions>
              <ActionBar align="right">
                <el-button plain @click="openFileBrowser('folder', 'galleryFolder')">选择目录</el-button>
                <el-button plain @click="openFileBrowser('image', 'galleryFiles')">选择图片</el-button>
              </ActionBar>
            </template>

            <div class="gallery-register-grid">
              <div class="soft-panel">
                <h3>注册目录</h3>
                <el-input v-model="galleryFolderPath" placeholder="请选择或输入图片目录" />
                <div class="register-options">
                  <el-checkbox v-model="registerRecursive">递归读取子目录</el-checkbox>
                </div>
                <div class="register-actions">
                  <el-button type="primary" :loading="registeringGallery" :disabled="isRunning" @click="handleRegisterFolder">
                    注册目录图片
                  </el-button>
                </div>
              </div>

              <div class="soft-panel">
                <h3>注册图片文件</h3>
                <el-input
                  v-model="galleryFilePathsText"
                  type="textarea"
                  :rows="5"
                  placeholder="每行一个图片路径，也可以通过文件浏览器选择。"
                />
                <div class="register-actions">
                  <el-button type="primary" :loading="registeringGallery" :disabled="isRunning" @click="handleRegisterFiles">
                    注册图片文件
                  </el-button>
                </div>
              </div>
            </div>

            <div class="top-gap">
              <TerminalLogPanel title="图库任务日志" :logs="logs" :is-running="isRunning" :status="galleryTaskStatus" />
            </div>

            <div class="stats-grid compact-grid">
              <StatCard label="图片记录" :value="String(overview.total_images)" hint="gallery_image 记录数" number />
              <StatCard label="特征记录" :value="String(overview.total_features)" hint="所有模型版本的特征总数" number />
              <StatCard label="唯一车辆" :value="String(overview.total_vehicles)" hint="vehicle_identity 记录数" number />
            </div>

            <el-table :data="galleryImages" v-loading="loadingGallery" style="width: 100%">
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="vehicle_id" label="车辆 ID" width="140" show-overflow-tooltip />
              <el-table-column prop="cam_id" label="摄像头" width="120" show-overflow-tooltip />
              <el-table-column prop="img_path" label="图片路径" min-width="360" show-overflow-tooltip />
              <el-table-column prop="feature_count" label="引用特征" width="110" />
              <el-table-column label="操作" width="110" align="center">
                <template #default="scope">
                  <el-button size="small" plain type="danger" :disabled="scope.row.feature_count > 0" @click="handleDeleteImage(scope.row)">
                    删除记录
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrap">
              <el-pagination
                layout="prev, pager, next"
                :total="galleryTotal"
                :page-size="galleryPageSize"
                v-model:current-page="galleryPage"
                @current-change="loadGalleryImages"
              />
            </div>
          </SectionCard>

          <SectionCard
            v-if="activeMenu === 'models'"
            eyebrow="Models"
            title="模型配置"
            description="管理员维护模型档案。用户只能在已启用、已发布且有可用版本的模型中选择。"
          >
            <template #actions>
              <ActionBar align="right">
                <el-button plain :loading="loadingModels" @click="loadModels">刷新模型</el-button>
                <el-button type="primary" @click="openCreateProfileDialog">新增模型档案</el-button>
              </ActionBar>
            </template>

            <div class="model-profile-list">
              <article
                v-for="profile in modelProfiles"
                :key="profile.id"
                class="model-profile-card"
                :class="{ inactive: !profile.is_enabled }"
              >
                <div class="profile-main">
                  <p class="profile-eyebrow">{{ profile.is_enabled ? '已启用' : '已停用' }} · {{ profile.is_public ? '前台可见' : '仅后台' }}</p>
                  <h3>{{ profile.name }}</h3>
                  <p>{{ profile.description || '管理员维护的模型档案。' }}</p>
                </div>

                <div class="profile-tags">
                  <el-tag effect="plain" round>{{ profile.global_feature_dim }} / {{ profile.full_feature_dim }} 维</el-tag>
                  <el-tag :type="profile.supports_concat ? 'success' : 'info'" effect="plain" round>Pro</el-tag>
                  <el-tag :type="profile.supports_rerank ? 'success' : 'info'" effect="plain" round>深度思考</el-tag>
                  <el-tag :type="profile.feature_status?.is_complete ? 'success' : 'warning'" effect="plain" round>
                    {{ profile.feature_status?.feature_count || 0 }} / {{ profile.feature_status?.image_count || 0 }} 特征
                  </el-tag>
                </div>

                <div class="profile-paths">
                  <span :title="profile.weights_file">权重 {{ profile.weights_file || '未配置' }}</span>
                  <span :title="profile.config_file">配置 {{ profile.config_file || '未配置' }}</span>
                  <span :title="profile.model_signature">签名 {{ profile.model_signature || '未生成' }}</span>
                </div>

                <ActionBar align="right">
                  <el-button size="small" plain @click="openEditProfileDialog(profile)">编辑</el-button>
                  <el-button size="small" plain @click="handlePublishProfile(profile)">
                    {{ profile.is_public ? '取消发布' : '发布给用户' }}
                  </el-button>
                  <el-button size="small" type="primary" plain :disabled="isRunning" @click="handleBuildFeatures(profile, false)">补齐特征</el-button>
                  <el-button size="small" plain :disabled="isRunning" @click="handleBuildFeatures(profile, true)">重建特征</el-button>
                  <el-button size="small" plain type="danger" @click="handleDeleteProfile(profile)">删除/停用</el-button>
                </ActionBar>
              </article>
            </div>

            <div class="top-gap">
              <TerminalLogPanel title="模型特征构建日志" :logs="logs" :is-running="isRunning" :status="galleryTaskStatus" />
            </div>
          </SectionCard>

          <SectionCard
            v-if="activeMenu === 'monitor'"
            eyebrow="Monitor"
            title="运行状态总览"
            description="上方看全局规模，下方按模型查看特征覆盖和公开状态。"
          >
            <template #actions>
              <ActionBar align="right">
                <el-button plain :loading="loadingOverview" @click="loadOverview">刷新总览</el-button>
              </ActionBar>
            </template>

            <div class="overview-strip">
              <StatCard label="图片记录" :value="String(overview.total_images)" number />
              <StatCard label="特征记录" :value="String(overview.total_features)" number />
              <StatCard label="公开模型" :value="String(overview.public_model_profile_count)" number />
              <StatCard label="运行设备" :value="overview.model_device || '未知'" text />
            </div>

            <el-form label-position="top" class="top-gap">
              <el-form-item label="查看模型详情">
                <el-select v-model="monitorProfileId" placeholder="请选择模型">
                  <el-option v-for="profile in monitorProfiles" :key="profile.id" :label="profile.name" :value="profile.id" />
                </el-select>
              </el-form-item>
            </el-form>

            <div v-if="monitorProfile" class="monitor-detail">
              <div>
                <p class="profile-eyebrow">{{ monitorProfile.is_public ? '前台可见' : '仅后台' }}</p>
                <h3>{{ monitorProfile.name }}</h3>
                <p>{{ monitorProfile.description || '暂无描述。' }}</p>
              </div>
              <div class="overview-strip small">
                <StatCard label="完整维度" :value="String(monitorProfile.full_feature_dim)" number />
                <StatCard label="已建特征" :value="String(monitorProfile.feature_status?.feature_count || 0)" number />
                <StatCard label="缺失特征" :value="String(monitorProfile.feature_status?.missing_count || 0)" number />
              </div>
            </div>
          </SectionCard>

          <SectionCard v-if="activeMenu === 'logs'" eyebrow="Logs" title="系统操作日志" description="按时间顺序查看登录、检索和后台操作记录。">
            <template #actions>
              <ActionBar align="right">
                <el-button plain :loading="loadingLogs" @click="loadLogs">刷新日志</el-button>
              </ActionBar>
            </template>

            <el-table :data="logList" v-loading="loadingLogs" style="width: 100%">
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="user_id" label="用户 ID" width="100" />
              <el-table-column prop="operation" label="操作内容" min-width="280" show-overflow-tooltip />
              <el-table-column prop="status" label="结果" width="100">
                <template #default="scope">
                  <el-tag :type="scope.row.status ? 'success' : 'danger'" effect="plain" round>
                    {{ scope.row.status ? '成功' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="exec_time" label="执行时间" width="190">
                <template #default="scope">{{ formatDateTime(scope.row.exec_time) }}</template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrap">
              <el-pagination layout="prev, pager, next" :total="totalLogs" :page-size="pageSize" v-model:current-page="currentPage" @current-change="loadLogs" />
            </div>
          </SectionCard>

          <SectionCard v-if="activeMenu === 'users'" eyebrow="Users" title="账号与权限" description="维护系统账号和角色权限。">
            <template #actions>
              <ActionBar align="right">
                <el-button plain :loading="loadingUsers" @click="loadUsers">刷新列表</el-button>
                <el-button type="primary" @click="showCreateDialog = true">新增账号</el-button>
              </ActionBar>
            </template>

            <el-table :data="userList" v-loading="loadingUsers" style="width: 100%">
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="username" label="用户名" min-width="180" show-overflow-tooltip />
              <el-table-column prop="role" label="角色" width="140">
                <template #default="scope">
                  <el-tag effect="plain" round>{{ scope.row.role === 'admin' ? '管理员' : '普通用户' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="create_time" label="创建时间" width="190">
                <template #default="scope">{{ formatDateTime(scope.row.create_time) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="110" align="center">
                <template #default="scope">
                  <el-button size="small" plain @click="openEditDialog(scope.row)">编辑</el-button>
                </template>
              </el-table-column>
            </el-table>
          </SectionCard>
        </main>
      </div>
    </div>

    <el-dialog v-model="showProfileDialog" :title="profileDialogTitle" width="760px">
      <el-form :model="profileForm" label-position="top" class="profile-dialog-form">
        <div class="settings-inline-grid">
          <el-form-item label="模型名称">
            <el-input v-model="profileForm.name" placeholder="例如 S10 Pro 2560" />
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="profileForm.display_order" :min="0" :max="9999" />
          </el-form-item>
        </div>

        <el-form-item label="描述">
          <el-input v-model="profileForm.description" type="textarea" :rows="2" placeholder="简短记录模型来源、训练轮次或用途" />
        </el-form-item>

        <div class="settings-inline-grid">
          <el-form-item label="启用状态">
            <el-switch v-model="profileForm.is_enabled" active-text="启用" inactive-text="停用" />
          </el-form-item>
          <el-form-item label="前台可选">
            <el-switch v-model="profileForm.is_public" active-text="发布" inactive-text="隐藏" />
          </el-form-item>
        </div>

        <div class="settings-inline-grid">
          <el-form-item label="支持 Pro concat">
            <el-switch v-model="profileForm.supports_concat" active-text="支持" inactive-text="不支持" />
          </el-form-item>
          <el-form-item label="支持深度思考">
            <el-switch v-model="profileForm.supports_rerank" active-text="支持" inactive-text="不支持" />
          </el-form-item>
        </div>

        <div class="settings-inline-grid">
          <el-form-item label="全局特征维度">
            <el-input-number v-model="profileForm.global_feature_dim" :min="1" :max="10000" />
          </el-form-item>
          <el-form-item label="完整特征维度">
            <el-input-number v-model="profileForm.full_feature_dim" :min="profileForm.global_feature_dim" :max="10000" :disabled="!profileForm.supports_concat" />
          </el-form-item>
        </div>

        <el-collapse class="profile-advanced">
          <el-collapse-item title="高级字段：权重、配置与推理模式" name="advanced">
            <el-form-item label="权重文件">
              <div class="input-with-action">
                <el-input v-model="profileForm.weights_file" placeholder="从 outputs 中选择权重文件" />
                <el-button plain @click="openFileBrowser('weights', 'weights')">选择</el-button>
              </div>
            </el-form-item>

            <el-form-item label="推理配置文件">
              <div class="input-with-action">
                <el-input v-model="profileForm.config_file" placeholder="从 configs 中选择部署配置" />
                <el-button plain @click="openFileBrowser('config', 'config')">选择</el-button>
              </div>
            </el-form-item>

            <div class="settings-inline-grid">
              <el-form-item label="Fast 推理模式">
                <el-input v-model="profileForm.fast_inference_mode" placeholder="global" />
              </el-form-item>
              <el-form-item label="Pro 推理模式">
                <el-input v-model="profileForm.pro_inference_mode" :disabled="!profileForm.supports_concat" placeholder="global_detail" />
              </el-form-item>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-form>

      <template #footer>
        <ActionBar align="right">
          <el-button plain @click="showProfileDialog = false">取消</el-button>
          <el-button type="primary" :loading="savingProfile" @click="handleSaveProfile">保存模型档案</el-button>
        </ActionBar>
      </template>
    </el-dialog>

    <el-dialog v-model="showFileBrowser" :title="fileBrowserTitle" width="820px">
      <div class="browser-toolbar">
        <el-select v-model="browserRoot" placeholder="根目录" @change="browsePath(browserRoot)">
          <el-option v-for="root in browserRoots" :key="root" :label="root" :value="root" />
        </el-select>
        <el-input v-model="browserPath" readonly />
        <el-button plain @click="browseParent">上一级</el-button>
      </div>

      <el-table :data="browserEntries" v-loading="loadingBrowser" max-height="440">
        <el-table-column prop="name" label="名称" min-width="260" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="110" />
        <el-table-column prop="path" label="路径" min-width="300" show-overflow-tooltip />
        <el-table-column label="操作" width="120" align="center">
          <template #default="scope">
            <el-button v-if="scope.row.type === 'directory'" size="small" plain @click="browsePath(scope.row.path)">打开</el-button>
            <el-button v-else size="small" type="primary" plain @click="selectBrowserEntry(scope.row)">选择</el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <ActionBar align="right">
          <el-button v-if="browserKind === 'folder'" type="primary" @click="selectCurrentBrowserFolder">选择当前目录</el-button>
          <el-button plain @click="showFileBrowser = false">关闭</el-button>
        </ActionBar>
      </template>
    </el-dialog>

    <el-dialog v-model="showCreateDialog" title="新增账号" width="520px">
      <el-form :model="createForm" label-position="top">
        <el-form-item label="用户名"><el-input v-model="createForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="createForm.password" type="password" show-password /></el-form-item>
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

    <el-dialog v-model="showEditDialog" title="编辑账号" width="520px">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="用户名"><el-input v-model="editForm.username" /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="editForm.password" type="password" show-password placeholder="留空则不修改" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button plain type="danger" :disabled="editingUser?.is_builtin" @click="handleDeleteUser(editingUser)">删除账号</el-button>
          <ActionBar align="right">
            <el-button plain @click="showEditDialog = false">取消</el-button>
            <el-button type="primary" :loading="savingUser" @click="handleSaveUser">保存账号</el-button>
          </ActionBar>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import ActionBar from '@/components/base/action-bar.vue'
import AdminNav from '@/components/admin/admin-nav.vue'
import PageHeader from '@/components/base/page-header.vue'
import SectionCard from '@/components/base/section-card.vue'
import StatCard from '@/components/base/stat-card.vue'
import TerminalLogPanel from '@/components/admin/terminal-log-panel.vue'
import { useGalleryPolling } from '@/composables/use-gallery-polling'
import { useSession } from '@/composables/use-session'
import { formatDateTime, normalizeModelState, normalizeProfile } from '@/utils/formatters'
import {
  browseServerFiles,
  buildModelFeatures,
  clearGalleryRecords,
  createModelProfile,
  createUser,
  deleteGalleryImage,
  deleteModelProfile,
  deleteUser,
  fetchAdminOverview,
  fetchAuditLogs,
  fetchGalleryImages,
  fetchModelProfiles,
  fetchModelState,
  fetchSystemConfig,
  fetchUsers,
  openNativeFileDialog,
  publishModelProfile,
  registerGalleryFiles,
  registerGalleryFolder,
  saveSystemConfig,
  updateModelProfile,
  updateUser
} from '@/api/admin'

const router = useRouter()
const { syncSession, logoutAndRedirect } = useSession(router)
const { status: galleryTaskStatus, isRunning, logs, refreshStatus, startPolling, setPollInterval } = useGalleryPolling()

const menuItems = [
  { key: 'settings', index: '01', label: '系统设置', description: '设备、阈值与浏览范围' },
  { key: 'gallery', index: '02', label: '图库图片', description: '注册与管理图片记录' },
  { key: 'models', index: '03', label: '模型配置', description: '档案、发布与特征构建' },
  { key: 'monitor', index: '04', label: '运行监控', description: '规模和模型覆盖状态' },
  { key: 'logs', index: '05', label: '操作日志', description: '审计后台操作记录' },
  { key: 'users', index: '06', label: '账号权限', description: '管理用户与角色' }
]

const activeMenu = ref('settings')
const loadingConfig = ref(false)
const savingConfig = ref(false)
const loadingOverview = ref(false)
const loadingModels = ref(false)
const loadingGallery = ref(false)
const registeringGallery = ref(false)
const loadingLogs = ref(false)
const loadingUsers = ref(false)
const savingProfile = ref(false)
const showProfileDialog = ref(false)
const editingProfileId = ref(null)
const modelProfiles = ref([])
const galleryImages = ref([])
const galleryTotal = ref(0)
const galleryPage = ref(1)
const galleryPageSize = 12
const galleryFolderPath = ref('')
const galleryFilePathsText = ref('')
const registerRecursive = ref(true)
const monitorProfileId = ref(0)
const currentPage = ref(1)
const pageSize = 15
const totalLogs = ref(0)
const logList = ref([])
const userList = ref([])
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const creatingUser = ref(false)
const savingUser = ref(false)
const editingUser = ref(null)
const showFileBrowser = ref(false)
const loadingBrowser = ref(false)
const browserKind = ref('image')
const browserTarget = ref('')
const browserPath = ref('')
const browserRoot = ref('')
const browserRoots = ref([])
const browserEntries = ref([])

const sysConfig = reactive({
  model_device: 'cpu',
  similarity_threshold: 0.5,
  max_results: 50,
  search_default_top_k: 10,
  max_deep_thinking_gallery_size: 5000,
  deep_thinking_candidate_limit_min: 100,
  deep_thinking_candidate_limit_max: 500,
  gallery_poll_interval_ms: 1500,
  allowed_query_suffixes_text: '.jpg, .jpeg, .png, .bmp, .webp',
  file_browser_roots_text: '',
  log_level: 'INFO'
})

const overview = reactive({
  total_images: 0,
  total_features: 0,
  total_vehicles: 0,
  public_model_profile_count: 0,
  model_device: 'cpu',
  initialized: false,
  total_users: 0,
  total_logs: 0
})

const profileForm = reactive({
  name: '',
  description: '',
  is_enabled: true,
  is_public: true,
  display_order: 0,
  weights_file: '',
  config_file: '',
  supports_concat: false,
  supports_rerank: true,
  global_feature_dim: 2048,
  full_feature_dim: 2048,
  fast_inference_mode: 'global',
  pro_inference_mode: 'global_detail'
})

const createForm = reactive({ username: '', password: '', role: 'user' })
const editForm = reactive({ id: 0, username: '', password: '', role: 'user' })

const profileDialogTitle = computed(() => (editingProfileId.value ? '编辑模型档案' : '新增模型档案'))
const fileBrowserTitle = computed(() => ({ weights: '选择权重文件', config: '选择推理配置', image: '选择图库图片', folder: '选择图库目录' }[browserKind.value] || '文件浏览器'))
const monitorProfiles = computed(() => modelProfiles.value)
const monitorProfile = computed(() => monitorProfiles.value.find((item) => Number(item.id) === Number(monitorProfileId.value)) || null)

const parseCommaList = (value, fallback = []) => {
  const items = String(value || '').split(',').map((item) => item.trim()).filter(Boolean)
  return items.length ? items : fallback
}

const parseLines = (value) => String(value || '').split(/\r?\n/).map((item) => item.trim()).filter(Boolean)

const loadConfig = async () => {
  loadingConfig.value = true
  try {
    const response = await fetchSystemConfig()
    Object.assign(sysConfig, {
      model_device: response.data?.model_device || 'cpu',
      similarity_threshold: Number(response.data?.similarity_threshold ?? 0.5),
      max_results: Number(response.data?.max_results ?? 50),
      search_default_top_k: Number(response.data?.search_default_top_k ?? 10),
      max_deep_thinking_gallery_size: Number(response.data?.max_deep_thinking_gallery_size ?? 5000),
      deep_thinking_candidate_limit_min: Number(response.data?.deep_thinking_candidate_limit_min ?? 100),
      deep_thinking_candidate_limit_max: Number(response.data?.deep_thinking_candidate_limit_max ?? 500),
      gallery_poll_interval_ms: Number(response.data?.gallery_poll_interval_ms ?? 1500),
      allowed_query_suffixes_text: Array.isArray(response.data?.allowed_query_suffixes) ? response.data.allowed_query_suffixes.join(', ') : '.jpg, .jpeg, .png, .bmp, .webp',
      file_browser_roots_text: Array.isArray(response.data?.file_browser_roots) ? response.data.file_browser_roots.join('\n') : '',
      log_level: response.data?.log_level || 'INFO'
    })
    setPollInterval(sysConfig.gallery_poll_interval_ms)
  } finally {
    loadingConfig.value = false
  }
}

const handleSaveConfig = async () => {
  savingConfig.value = true
  try {
    await saveSystemConfig({
      model_device: sysConfig.model_device,
      similarity_threshold: Number(sysConfig.similarity_threshold),
      max_results: Number(sysConfig.max_results),
      search_default_top_k: Number(sysConfig.search_default_top_k),
      max_deep_thinking_gallery_size: Number(sysConfig.max_deep_thinking_gallery_size),
      deep_thinking_candidate_limit_min: Number(sysConfig.deep_thinking_candidate_limit_min),
      deep_thinking_candidate_limit_max: Number(sysConfig.deep_thinking_candidate_limit_max),
      gallery_poll_interval_ms: Number(sysConfig.gallery_poll_interval_ms),
      allowed_query_suffixes: parseCommaList(sysConfig.allowed_query_suffixes_text, ['.jpg', '.jpeg', '.png', '.bmp', '.webp']),
      file_browser_roots: parseLines(sysConfig.file_browser_roots_text),
      log_level: sysConfig.log_level
    })
    await loadConfig()
    ElMessage.success('系统参数已保存。')
  } finally {
    savingConfig.value = false
  }
}

const loadOverview = async () => {
  loadingOverview.value = true
  try {
    const response = await fetchAdminOverview()
    Object.assign(overview, {
      total_images: Number(response.data?.total_images ?? 0),
      total_features: Number(response.data?.total_features ?? 0),
      total_vehicles: Number(response.data?.total_vehicles ?? 0),
      public_model_profile_count: Number(response.data?.public_model_profile_count ?? 0),
      model_device: response.data?.model_device || 'cpu',
      initialized: Boolean(response.data?.initialized),
      total_users: Number(response.data?.total_users ?? 0),
      total_logs: Number(response.data?.total_logs ?? 0)
    })
    if (Array.isArray(response.data?.model_profiles)) {
      modelProfiles.value = response.data.model_profiles.map(normalizeProfile)
      if (!monitorProfileId.value && modelProfiles.value.length) {
        monitorProfileId.value = modelProfiles.value[0].id
      }
    }
  } finally {
    loadingOverview.value = false
  }
}

const loadModels = async () => {
  loadingModels.value = true
  try {
    const response = await fetchModelProfiles()
    modelProfiles.value = Array.isArray(response.data?.items) ? response.data.items.map(normalizeProfile) : []
    if (!monitorProfileId.value && modelProfiles.value.length) {
      monitorProfileId.value = modelProfiles.value[0].id
    }
  } finally {
    loadingModels.value = false
  }
}

const loadModelState = async () => {
  const response = await fetchModelState()
  const state = normalizeModelState(response.data)
  modelProfiles.value = state.modelProfiles
}

const loadGalleryImages = async () => {
  loadingGallery.value = true
  try {
    const response = await fetchGalleryImages(galleryPage.value, galleryPageSize)
    galleryImages.value = Array.isArray(response.data?.items) ? response.data.items : []
    galleryTotal.value = Number(response.data?.total ?? 0)
  } finally {
    loadingGallery.value = false
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

const handleMenuSelect = async (key) => {
  activeMenu.value = key
  if (key === 'gallery') await loadGalleryImages()
  if (key === 'models') await Promise.all([loadModels(), refreshStatus().catch(() => null)])
  if (key === 'monitor') await loadOverview()
  if (key === 'logs') await loadLogs()
  if (key === 'users') await loadUsers()
}

const resetProfileForm = () => {
  Object.assign(profileForm, {
    name: '',
    description: '',
    is_enabled: true,
    is_public: true,
    display_order: 0,
    weights_file: '',
    config_file: '',
    supports_concat: false,
    supports_rerank: true,
    global_feature_dim: 2048,
    full_feature_dim: 2048,
    fast_inference_mode: 'global',
    pro_inference_mode: 'global_detail'
  })
}

const openCreateProfileDialog = () => {
  editingProfileId.value = null
  resetProfileForm()
  showProfileDialog.value = true
}

const openEditProfileDialog = (profile) => {
  editingProfileId.value = profile.id
  Object.assign(profileForm, {
    name: profile.name,
    description: profile.description,
    is_enabled: profile.is_enabled,
    is_public: profile.is_public,
    display_order: profile.display_order,
    weights_file: profile.weights_file,
    config_file: profile.config_file,
    supports_concat: profile.supports_concat,
    supports_rerank: profile.supports_rerank,
    global_feature_dim: profile.global_feature_dim || 2048,
    full_feature_dim: profile.full_feature_dim || profile.global_feature_dim || 2048,
    fast_inference_mode: profile.fast_inference_mode || 'global',
    pro_inference_mode: profile.pro_inference_mode || 'global_detail'
  })
  showProfileDialog.value = true
}

const buildProfilePayload = () => {
  const globalDim = Number(profileForm.global_feature_dim)
  const fullDim = profileForm.supports_concat ? Number(profileForm.full_feature_dim) : globalDim
  return {
    name: profileForm.name.trim(),
    description: profileForm.description,
    is_enabled: Boolean(profileForm.is_enabled),
    is_public: Boolean(profileForm.is_public),
    display_order: Number(profileForm.display_order),
    weights_file: profileForm.weights_file,
    config_file: profileForm.config_file,
    supports_concat: Boolean(profileForm.supports_concat),
    supports_rerank: Boolean(profileForm.supports_rerank),
    global_feature_dim: globalDim,
    full_feature_dim: fullDim,
    fast_inference_mode: profileForm.fast_inference_mode || 'global',
    pro_inference_mode: profileForm.supports_concat ? (profileForm.pro_inference_mode || 'global_detail') : 'global'
  }
}

const handleSaveProfile = async () => {
  savingProfile.value = true
  try {
    const payload = buildProfilePayload()
    if (editingProfileId.value) {
      await updateModelProfile(editingProfileId.value, payload)
    } else {
      await createModelProfile(payload)
    }
    showProfileDialog.value = false
    await Promise.all([loadModels(), loadOverview()])
    ElMessage.success('模型档案已保存。')
  } finally {
    savingProfile.value = false
  }
}

const handlePublishProfile = async (profile) => {
  await publishModelProfile(profile.id, !profile.is_public)
  await loadModels()
  ElMessage.success(profile.is_public ? '已取消发布。' : '已发布给用户。')
}

const handleBuildFeatures = async (profile, rebuild) => {
  if (rebuild) {
    await ElMessageBox.confirm('这会清空该模型版本已有特征并重新构建，图片记录不会删除。是否继续？', '重建模型特征', {
      confirmButtonText: '继续',
      cancelButtonText: '取消',
      type: 'warning'
    })
  }
  await buildModelFeatures(profile.id, rebuild)
  startPolling()
  await refreshStatus().catch(() => null)
  ElMessage.success('已开始构建模型特征。')
}

const handleDeleteProfile = async (profile) => {
  await ElMessageBox.confirm('如果模型已有特征引用，将停用而不是硬删除。是否继续？', '删除或停用模型档案', {
    confirmButtonText: '继续',
    cancelButtonText: '取消',
    type: 'warning'
  })
  await deleteModelProfile(profile.id)
  await Promise.all([loadModels(), loadOverview()])
  ElMessage.success('模型档案已更新。')
}

const handleRegisterFolder = async () => {
  if (!galleryFolderPath.value.trim()) {
    ElMessage.warning('请先选择图库目录。')
    return
  }
  registeringGallery.value = true
  try {
    await registerGalleryFolder(galleryFolderPath.value.trim(), registerRecursive.value)
    startPolling()
    await refreshStatus().catch(() => null)
    ElMessage.success('已开始注册目录图片，可在图库任务日志中查看进度。')
  } finally {
    registeringGallery.value = false
  }
}

const handleRegisterFiles = async () => {
  const paths = parseLines(galleryFilePathsText.value)
  if (!paths.length) {
    ElMessage.warning('请先选择或输入图片路径。')
    return
  }
  registeringGallery.value = true
  try {
    await registerGalleryFiles(paths)
    startPolling()
    await refreshStatus().catch(() => null)
    ElMessage.success('已开始注册图片文件，可在图库任务日志中查看进度。')
  } finally {
    registeringGallery.value = false
  }
}

const handleDeleteImage = async (image) => {
  await ElMessageBox.confirm('只删除数据库图片记录，不删除磁盘图片文件。是否继续？', '删除图片记录', {
    confirmButtonText: '删除记录',
    cancelButtonText: '取消',
    type: 'warning'
  })
  await deleteGalleryImage(image.id)
  await Promise.all([loadGalleryImages(), loadOverview()])
  ElMessage.success('图片记录已删除。')
}

const openFileBrowser = async (kind, target) => {
  browserKind.value = kind
  browserTarget.value = target
  try {
    const response = await openNativeFileDialog(kind)
    const data = response.data || {}
    if (!data.selected) return

    const values = Array.isArray(data.values) ? data.values : []
    const firstValue = data.value || values[0] || ''
    if (target === 'weights') profileForm.weights_file = firstValue
    if (target === 'config') profileForm.config_file = firstValue
    if (target === 'galleryFolder') galleryFolderPath.value = firstValue
    if (target === 'galleryFiles') {
      const current = parseLines(galleryFilePathsText.value)
      values.forEach((value) => {
        if (value && !current.includes(value)) current.push(value)
      })
      galleryFilePathsText.value = current.join('\n')
    }
  } catch {
    ElMessage.warning('系统文件选择窗口不可用，已切换为备用浏览器。')
    showFileBrowser.value = true
    await browsePath('')
  }
}

const browsePath = async (path) => {
  loadingBrowser.value = true
  try {
    const response = await browseServerFiles({ kind: browserKind.value, path: path || undefined })
    browserPath.value = response.data?.path || ''
    browserRoots.value = Array.isArray(response.data?.roots) ? response.data.roots : []
    browserRoot.value = browserRoots.value.find((root) => browserPath.value.startsWith(root)) || browserRoots.value[0] || ''
    browserEntries.value = Array.isArray(response.data?.entries) ? response.data.entries : []
  } finally {
    loadingBrowser.value = false
  }
}

const browseParent = () => {
  if (!browserPath.value) return
  const normalized = browserPath.value.replace(/\\/g, '/')
  const parent = normalized.split('/').slice(0, -1).join('/')
  if (parent) browsePath(parent)
}

const selectBrowserEntry = (entry) => {
  if (browserTarget.value === 'weights') profileForm.weights_file = entry.value
  if (browserTarget.value === 'config') profileForm.config_file = entry.value
  if (browserTarget.value === 'galleryFiles') {
    const current = parseLines(galleryFilePathsText.value)
    if (!current.includes(entry.value)) current.push(entry.value)
    galleryFilePathsText.value = current.join('\n')
  }
  showFileBrowser.value = false
}

const selectCurrentBrowserFolder = () => {
  if (browserTarget.value === 'galleryFolder') galleryFolderPath.value = browserPath.value
  showFileBrowser.value = false
}

const handleCreateUser = async () => {
  if (!createForm.username.trim() || !createForm.password.trim()) {
    ElMessage.warning('请先填写用户名和密码。')
    return
  }
  creatingUser.value = true
  try {
    await createUser({ username: createForm.username.trim(), password: createForm.password, role: createForm.role })
    showCreateDialog.value = false
    Object.assign(createForm, { username: '', password: '', role: 'user' })
    await Promise.all([loadUsers(), loadOverview()])
    ElMessage.success('账号已创建。')
  } finally {
    creatingUser.value = false
  }
}

const openEditDialog = (user) => {
  editingUser.value = user
  Object.assign(editForm, { id: user.id, username: user.username, password: '', role: user.role })
  showEditDialog.value = true
}

const handleSaveUser = async () => {
  savingUser.value = true
  try {
    const payload = { username: editForm.username.trim(), role: editForm.role }
    if (editForm.password.trim()) payload.password = editForm.password
    await updateUser(editForm.id, payload)
    showEditDialog.value = false
    await Promise.all([loadUsers(), loadOverview()])
    ElMessage.success('账号信息已更新。')
  } finally {
    savingUser.value = false
  }
}

const handleDeleteUser = async (user) => {
  if (!user?.id) return
  await ElMessageBox.confirm('删除后该账号将无法继续登录，是否继续？', '删除账号', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  })
  await deleteUser(user.id)
  showEditDialog.value = false
  await Promise.all([loadUsers(), loadOverview()])
  ElMessage.success('账号已删除。')
}

const handleLogout = async () => {
  await logoutAndRedirect()
  ElMessage.success('已退出登录。')
}

onMounted(async () => {
  syncSession()
  await Promise.all([
    loadConfig(),
    loadOverview(),
    loadModelState().catch(() => null),
    loadLogs(),
    refreshStatus().catch(() => null)
  ])
})

watch(isRunning, async (running, wasRunning) => {
  if (wasRunning && !running) {
    await Promise.all([loadGalleryImages(), loadOverview(), loadModels()])
  }
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
  min-width: 0;
}

.settings-form,
.profile-dialog-form {
  min-width: 0;
}

.settings-inline-grid,
.gallery-register-grid,
.stats-grid,
.overview-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.stats-grid,
.overview-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.overview-strip.small {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.soft-panel,
.monitor-detail {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.40);
  box-shadow: var(--shadow-ring);
  backdrop-filter: blur(14px) saturate(1.12);
}

.soft-panel h3,
.monitor-detail h3 {
  margin: 0 0 12px;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 500;
}

.register-options,
.register-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.register-actions {
  justify-content: flex-start;
}

.model-profile-list {
  display: grid;
  gap: 12px;
}

.model-profile-card {
  min-width: 0;
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(171, 96, 67, 0.22);
  border-radius: 8px;
  background: rgba(255, 250, 244, 0.52);
  box-shadow: 0 14px 34px rgba(91, 55, 38, 0.08);
  backdrop-filter: blur(14px) saturate(1.12);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.model-profile-card:hover {
  border-color: rgba(201, 100, 66, 0.34);
  background: rgba(255, 250, 244, 0.68);
  box-shadow: 0 18px 40px rgba(91, 55, 38, 0.12), 0 0 0 4px rgba(201, 100, 66, 0.06);
}

.model-profile-card.inactive {
  opacity: 0.68;
}

.profile-main {
  min-width: 0;
}

.profile-eyebrow {
  margin: 0 0 6px;
  color: #a75f42;
  font-size: 12px;
  font-weight: 700;
}

.profile-main h3 {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.profile-main p,
.monitor-detail p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  line-height: 1.55;
}

.profile-tags,
.profile-paths {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.profile-paths span {
  max-width: 100%;
  overflow: hidden;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-advanced {
  overflow: hidden;
  border: 1px solid rgba(171, 96, 67, 0.18);
  border-top: 1px solid rgba(171, 96, 67, 0.18);
  border-bottom: 1px solid rgba(171, 96, 67, 0.18);
  border-radius: 8px;
  background: rgba(255, 250, 244, 0.68);
  box-shadow: var(--shadow-ring);
}

.profile-advanced :deep(.el-collapse-item__header) {
  height: 48px;
  padding: 0 14px;
  border-bottom: 1px solid rgba(232, 225, 212, 0.9);
  background: rgba(255, 250, 244, 0.78);
  color: var(--text-primary);
  font-weight: 600;
}

.profile-advanced :deep(.el-collapse-item__wrap) {
  border-bottom: 0;
  background: transparent;
}

.profile-advanced :deep(.el-collapse-item__content) {
  padding: 16px 14px 14px;
  color: var(--text-primary);
}

.profile-advanced :deep(.el-collapse) {
  border: 0;
}

.input-with-action,
.browser-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  min-width: 0;
}

.browser-toolbar {
  margin-bottom: 14px;
}

.input-with-action .el-input,
.browser-toolbar .el-input {
  min-width: 0;
}

.compact-grid,
.top-gap {
  margin-top: 18px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
}

@media (max-width: 1180px) {
  .admin-layout,
  .settings-inline-grid,
  .gallery-register-grid,
  .stats-grid,
  .overview-strip,
  .overview-strip.small {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .dialog-footer,
  .input-with-action,
  .browser-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .header-meta {
    justify-content: flex-start;
  }
}
</style>
