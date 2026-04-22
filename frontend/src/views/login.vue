<template>
  <div class="login-page">
    <section class="brand-panel">
      <p class="brand-eyebrow">Vehicle ReID Console</p>
      <h1>基于深度卷积神经网络的车辆重识别系统的设计与实现</h1>
      <p class="brand-copy">
        Design and Implementation of a Vehicle Re-identification System Based on Deep Convolutional Neural Networks
      </p>

      <div class="workflow-rail">
        <div class="workflow-step">
          <span>01</span>
          <strong>Image Registry</strong>
          <p>图库图片先成为可追溯的数据记录。</p>
        </div>

        <div class="workflow-step">
          <span>02</span>
          <strong>Model Profiles</strong>
          <p>每个模型独立维护自己的特征版本。</p>
        </div>

        <div class="workflow-step">
          <span>03</span>
          <strong>Retrieval</strong>
          <p>用户选择模型后完成 Fast 或 Pro 检索。</p>
        </div>
      </div>
    </section>

    <section class="login-panel">
      <div class="panel-shell">
        <span class="panel-ribbon">Secure Access</span>
        <h2>登录系统</h2>
        <p class="panel-copy">请输入账号和密码以访问车辆检索系统。</p>

        <StatusBanner :tone="status.tone" :title="status.title" :message="status.message" />

        <el-form ref="loginFormRef" :model="loginForm" :rules="rules" label-position="top" class="login-form">
          <el-form-item label="账号" prop="username">
            <el-input v-model="loginForm.username" placeholder="请输入系统账号" clearable />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入访问密码"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <div class="helper-row">
            <span>登录成功后默认进入车辆检索前台。</span>
            <span>请联系管理员注册或进行其他操作</span>
          </div>

          <el-button type="primary" class="submit-button" :loading="loading" @click="handleLogin">
            {{ loading ? '正在验证身份...' : '进入系统' }}
          </el-button>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import StatusBanner from '@/components/base/status-banner.vue'
import { useSession } from '@/composables/use-session'
import { login } from '@/api/auth'

const router = useRouter()
const { persistSession } = useSession(router)
const loginFormRef = ref(null)
const loading = ref(false)
const status = ref({
  tone: 'neutral',
  title: '请使用已有账号登录',
  message: '请联系管理员注册或进行其他操作'
})

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = reactive({
  username: [{ required: true, message: '账号不能为空', trigger: 'blur' }],
  password: [{ required: true, message: '密码不能为空', trigger: 'blur' }]
})

const updateStatus = (tone, title, message) => {
  status.value = { tone, title, message }
}

const handleLogin = async () => {
  if (!loginFormRef.value) {
    return
  }

  try {
    await loginFormRef.value.validate()
  } catch {
    updateStatus('warning', '请补全登录信息', '账号和密码都是必填项。')
    return
  }

  loading.value = true
  updateStatus('info', '正在验证身份', '系统正在校验账号权限，请稍候。')

  try {
    const response = await login(loginForm.username, loginForm.password)
    persistSession({
      accessToken: response.access_token,
      role: response.role
    })
    updateStatus('success', '登录成功', '会话已建立，正在进入车辆检索前台。')
    ElMessage.success('登录成功')
    await router.push('/search')
  } catch {
    updateStatus('danger', '登录失败', '账号或密码不正确，或者后端服务暂时不可用。')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(360px, 1.1fr) minmax(360px, 0.9fr);
  gap: 24px;
  padding: 24px;
}

.brand-panel,
.panel-shell {
  border: 1px solid var(--border-soft);
  box-shadow: var(--shadow-whisper);
}

.brand-panel {
  padding: 56px 52px;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.44), rgba(250, 249, 245, 0.86));
}

.brand-eyebrow,
.card-eyebrow,
.panel-ribbon {
  display: inline-flex;
  align-items: center;
  color: var(--text-accent);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.brand-panel h1 {
  max-width: 12em;
  margin: 20px 0 16px;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: clamp(40px, 4.4vw, 62px);
  font-weight: 500;
  line-height: 1.12;
}

.brand-copy {
  max-width: 640px;
  margin: 0;
  color: var(--text-secondary);
  font-size: 18px;
  line-height: 1.65;
}

.workflow-rail {
  display: grid;
  gap: 12px;
  max-width: 620px;
  margin-top: 42px;
}

.workflow-step {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  column-gap: 16px;
  row-gap: 4px;
  align-items: start;
  padding: 16px 0;
  border-top: 1px solid rgba(201, 100, 66, 0.16);
}

.workflow-step span {
  grid-row: span 2;
  color: var(--text-accent);
  font-family: var(--font-number);
  font-size: 14px;
  font-weight: 700;
}

.workflow-step strong {
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 500;
  line-height: 1.2;
}

.workflow-step p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.login-panel {
  display: flex;
  align-items: center;
  justify-content: center;
}

.panel-shell {
  width: min(100%, 520px);
  padding: 32px;
  border-radius: 8px;
  background: rgba(250, 249, 245, 0.94);
}

.panel-shell h2 {
  margin: 18px 0 10px;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 38px;
  font-weight: 500;
}

.panel-copy {
  margin: 0 0 20px;
  color: var(--text-secondary);
  font-size: 15px;
}

.login-form {
  margin-top: 22px;
}

.helper-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 6px 0 22px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.submit-button {
  width: 100%;
}

@media (max-width: 1100px) {
  .login-page {
    grid-template-columns: 1fr;
  }

}

@media (max-width: 720px) {
  .login-page {
    gap: 18px;
    padding: 18px;
  }

  .brand-panel,
  .panel-shell {
    padding: 24px;
    border-radius: 8px;
  }

  .helper-row {
    flex-direction: column;
  }
}
</style>
