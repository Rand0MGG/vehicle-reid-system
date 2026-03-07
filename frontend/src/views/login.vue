<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2 class="login-title">计算机视觉项目系统登录</h2>
      <el-form ref="loginFormRef" :model="loginForm" :rules="rules" label-width="80px" label-position="top">
        <el-form-item label="系统账号" prop="username">
          <el-input v-model="loginForm.username" placeholder="请输入管理员账号" clearable />
        </el-form-item>
        <el-form-item label="访问密码" prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-button" :loading="loading" @click="handleLogin">验证并登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
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
  password: [{ required: true, message: '密码不可为空', trigger: 'blur' }]
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const response = await login(loginForm.username, loginForm.password)
        localStorage.setItem('access_token', response.access_token)
        ElMessage.success('身份验证成功')
        router.push('/search')
      } catch (error) {
        console.error(error)
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;
}
.login-card {
  width: 400px;
}
.login-title {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
}
.login-button {
  width: 100%;
}
</style>