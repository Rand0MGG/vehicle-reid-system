<template>
  <div class="login-container">
    <el-card shadow="never" class="apple-login-card">
      <div class="login-header">
        <h2 class="login-title">计算机视觉项目系统验证</h2>
        <p class="login-subtitle">请输入系统授权凭证以访问核心底层架构</p>
      </div>
      
      <el-form ref="loginFormRef" :model="loginForm" :rules="rules" label-width="80px" label-position="top">
        <el-form-item label="系统账号" prop="username">
          <el-input v-model="loginForm.username" placeholder="请输入操作实体账号" clearable class="macos-input" />
        </el-form-item>
        <el-form-item label="访问密码" prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入加密凭据" show-password @keyup.enter="handleLogin" class="macos-input" />
        </el-form-item>
        <el-form-item style="margin-top: 32px;">
          <el-button type="primary" class="apple-btn login-button" :loading="loading" @click="handleLogin">
            安全验证并接入系统
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'

const router = useRouter()
const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = reactive({
  username: [{ required: true, message: '账号不可为空', trigger: 'blur' }],
  password: [{ required: true, message: '加密凭据不可为空', trigger: 'blur' }]
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const response = await login(loginForm.username, loginForm.password)
        localStorage.setItem('access_token', response.access_token)
        ElMessage.success('身份验证通过，正在接入检索管线')
        router.push('/search')
      } catch (error) {
      } finally {
        loading.value = false
      }
    }
  })
}

onMounted(() => {
  document.documentElement.classList.add('dark')
})

onBeforeUnmount(() => {
  document.documentElement.classList.remove('dark')
})
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: transparent;
}

.apple-login-card {
  width: 440px;
  background: rgba(30, 30, 30, 0.65) !important;
  backdrop-filter: blur(40px) saturate(200%) !important;
  -webkit-backdrop-filter: blur(40px) saturate(200%) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
  border-radius: 24px !important;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.4) !important;
  padding: 20px;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title {
  color: #ffffff;
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.login-subtitle {
  color: #8e8e93;
  font-size: 14px;
  margin: 0;
}

.macos-input :deep(.el-input__wrapper) {
  background-color: rgba(0, 0, 0, 0.3) !important;
  border-radius: 12px !important;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05) inset !important;
  padding: 4px 12px;
}

.macos-input :deep(input) {
  color: #f5f5f7 !important;
}

.login-button {
  width: 100%;
  height: 44px;
  font-size: 16px;
  border-radius: 14px !important;
}
</style>