<template>
  <div class="admin-container">
    <div class="header-section">
      <h2>计算机视觉项目控制台</h2>
      <el-button type="primary" :loading="syncing" @click="handleSyncGallery">
        执行底库特征同步
      </el-button>
    </div>

    <el-tabs type="border-card">
      <el-tab-pane label="系统审计日志">
        <div class="card-header-actions">
          <el-button type="danger" size="small" @click="handleLogout">安全退出</el-button>
        </div>
        <el-table :data="logList" v-loading="loadingLogs" style="width: 100%" border>
          <el-table-column prop="id" label="记录标识" width="100" />
          <el-table-column prop="user_id" label="操作实体主键" width="120" />
          <el-table-column prop="operation" label="行为简述" />
          <el-table-column prop="status" label="执行状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.status ? 'success' : 'danger'">
                {{ scope.row.status ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="exec_time" label="发生时间" width="200">
            <template #default="scope">
              {{ formatTime(scope.row.exec_time) }}
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrapper">
          <el-pagination
            background
            layout="prev, pager, next, total"
            :total="totalLogs"
            :page-size="pageSize"
            v-model:current-page="currentPage"
            @current-change="handlePageChange"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="账户权限管理">
        <div class="action-bar">
          <el-button type="success" @click="showCreateDialog = true">新增账户实体</el-button>
        </div>
        <el-table :data="userList" v-loading="loadingUsers" style="width: 100%; margin-top: 15px;" border>
          <el-table-column prop="id" label="账户主键" width="100" />
          <el-table-column prop="username" label="登录账号" />
          <el-table-column prop="role" label="权限角色" width="150">
            <template #default="scope">
              <el-tag :type="scope.row.role === 'admin' ? 'warning' : 'info'">
                {{ scope.row.role === 'admin' ? '系统管理员' : '普通操作员' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="create_time" label="创建时间" width="200">
            <template #default="scope">
              {{ formatTime(scope.row.create_time) }}
            </template>
          </el-table-column>
          <el-table-column label="操作指令" width="150">
            <template #default="scope">
              <el-button type="danger" size="small" @click="handleDeleteUser(scope.row.id)" :disabled="scope.row.id === 1">
                移除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showCreateDialog" title="创建新账户实体" width="30%">
      <el-form :model="newUserForm" label-width="80px">
        <el-form-item label="登录账号">
          <el-input v-model="newUserForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="newUserForm.password" type="password" show-password autocomplete="off" />
        </el-form-item>
        <el-form-item label="分配角色">
          <el-select v-model="newUserForm.role" placeholder="请选择层级" style="width: 100%">
            <el-option label="普通操作员" value="user" />
            <el-option label="系统管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消执行</el-button>
          <el-button type="primary" @click="handleCreateUser" :loading="creatingUser">确认构建</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchAuditLogs, syncGalleryData, fetchUserList, createNewUser, removeUser } from '@/api/admin'
import { logout } from '@/api/auth'

const router = useRouter()
const loadingLogs = ref(false)
const loadingUsers = ref(false)
const syncing = ref(false)

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

const loadLogs = async () => {
  loadingLogs.value = true
  try {
    const response = await fetchAuditLogs(currentPage.value, pageSize.value)
    logList.value = response.data.items
    totalLogs.value = response.data.total
  } catch (error) {
    console.error(error)
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
    console.error(error)
  } finally {
    loadingUsers.value = false
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadLogs()
}

const handleSyncGallery = async () => {
  syncing.value = true
  try {
    await syncGalleryData()
    ElMessage.success('特征底库同步指令已下达执行')
  } catch (error) {
    console.error(error)
  } finally {
    syncing.value = false
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
    console.error(error)
  } finally {
    creatingUser.value = false
  }
}

const handleDeleteUser = async (id) => {
  try {
    await ElMessageBox.confirm('确认移除该账户实体？此操作不可逆。', '系统警告', {
      confirmButtonText: '执行移除',
      cancelButtonText: '放弃操作',
      type: 'warning'
    })
    await removeUser(id)
    ElMessage.success('账户实体已销毁')
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

const handleLogout = async () => {
  try {
    await logout()
  } catch (error) {
    console.error(error)
  } finally {
    localStorage.removeItem('access_token')
    router.push('/login')
  }
}

const formatTime = (timeStr) => {
  if (!timeStr) return '未知'
  return timeStr.replace('T', ' ').substring(0, 19)
}

onMounted(() => {
  loadLogs()
  loadUsers()
})
</script>

<style scoped>
.admin-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.card-header-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 15px;
}
.action-bar {
  display: flex;
  justify-content: flex-start;
}
.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>