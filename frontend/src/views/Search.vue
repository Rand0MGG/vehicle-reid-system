<template>
  <div class="search-layout">
    <div class="macos-topbar">
      <div class="topbar-left">
        <span class="system-brand">计算机视觉项目检索终端</span>
      </div>
      <div class="topbar-right">
        <el-button color="#ff453a" size="small" @click="handleLogout" class="apple-btn">断开安全连接</el-button>
      </div>
    </div>

    <div class="main-content">
      <el-card shadow="never" class="apple-control-panel">
        <el-row :gutter="32">
          <el-col :span="11">
            <el-upload
              class="macos-upload"
              drag
              action="#"
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleFileChange"
            >
              <div v-if="previewUrl" class="preview-box">
                <img :src="previewUrl" class="preview-img" />
                <div class="re-upload-glass-tip">触碰或拖拽替换目标图像</div>
              </div>
              <div v-else class="upload-placeholder">
                <el-icon class="upload-icon"><upload-filled /></el-icon>
                <div class="upload-text">
                  拖拽二维图像至此区域 或 <span>点击装载</span>
                </div>
              </div>
            </el-upload>
          </el-col>

          <el-col :span="13" class="action-col">
            <el-form label-position="top" class="macos-form">
              <el-form-item label="全局相似度截断截取量">
                <el-slider v-model="topK" :min="1" :max="20" show-input />
              </el-form-item>
              
              <el-form-item label="时间轴约束边界 (底层管线暂未贯通)">
                <el-date-picker
                  v-model="dateRange"
                  type="datetimerange"
                  range-separator="至"
                  start-placeholder="起始采样点"
                  end-placeholder="终止采样点"
                  disabled
                  class="macos-date-picker"
                />
              </el-form-item>

              <div class="btn-group">
                <el-button 
                  type="primary" 
                  size="large" 
                  :loading="loading" 
                  @click="handleSearch"
                  class="apple-btn execute-btn"
                >
                  {{ loading ? '卷积神经网络特征提取运算中...' : '发起视觉相似度全库检索' }}
                </el-button>
              </div>
            </el-form>
          </el-col>
        </el-row>
      </el-card>

      <div class="results-section" v-if="results.length > 0">
        <div class="section-divider">
          <span class="divider-text">底层检索序列返回 (运算开销: {{ timeCost }}s)</span>
        </div>
        
        <el-row :gutter="24">
          <el-col 
            v-for="(item, index) in results" 
            :key="index" 
            :xs="12" :sm="8" :md="6" :lg="4"
          >
            <el-card shadow="never" :body-style="{ padding: '0px' }" class="apple-result-card">
              <div class="image-wrapper">
                <el-image 
                  :src="item.img_url" 
                  fit="cover" 
                  class="result-img"
                  :preview-src-list="[item.img_url]" 
                  :initial-index="0"
                  preview-teleported
                  hide-on-click-modal
                  lazy
                />
                <div class="glass-score-badge" :class="getScoreClass(item.score)">
                  {{ (item.score * 100).toFixed(1) }}%
                </div>
              </div>
              <div class="glass-info-box">
                <div class="main-info">物理标识: {{ item.vehicle_id }}</div>
                <div class="sub-info">采集终端: {{ item.cam_id }}</div>
                <div class="sub-info">采样时间: {{ formatTime(item.capture_time) }}</div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
      
      <el-empty v-else-if="searched" description="特征空间内未命中有价值的相似车辆序列" class="macos-empty" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { searchVehicle } from '@/api/search'
import { logout } from '@/api/auth'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

const loading = ref(false)
const searched = ref(false)
const topK = ref(10)
const dateRange = ref([])
const file = ref(null)
const previewUrl = ref('')
const results = ref([])
const timeCost = ref(0)
const router = useRouter()

const handleFileChange = (uploadFile) => {
  file.value = uploadFile.raw
  previewUrl.value = URL.createObjectURL(uploadFile.raw)
  searched.value = false
  results.value = []
}

const handleSearch = async () => {
  if (!file.value) {
    ElMessage.warning('目标物理图像缺失，阻断检索执行')
    return
  }

  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    formData.append('top_k', topK.value)
    
    const res = await searchVehicle(formData)
    
    const { data } = res
    results.value = data.results
    timeCost.value = data.time_cost
    searched.value = true
    
    ElMessage.success(`神经网络检索执行完成，总耗时 ${data.time_cost} 秒`)
    
  } catch (error) {
  } finally {
    loading.value = false
  }
}

const getScoreClass = (score) => {
  if (score > 0.8) return 'score-high'
  if (score > 0.5) return 'score-mid'
  return 'score-low'
}

const formatTime = (timeStr) => {
  if (!timeStr) return '状态未知'
  return timeStr.replace('T', ' ')
}

const handleLogout = async () => {
  try {
    await logout()
  } catch (error) {
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    ElMessage.success('安全凭证已注销')
    router.push('/login')
  }
}

onMounted(() => {
  document.documentElement.classList.add('dark')
})

onBeforeUnmount(() => {
  document.documentElement.classList.remove('dark')
})
</script>

<style scoped>
.search-layout {
  height: 100vh; /* 关键修复：由 min-height 改为严格约束的 height，强制收束在视口内 */
  display: flex;
  flex-direction: column;
  background-color: transparent;
}

.macos-topbar {
  height: 56px;
  background: rgba(30, 30, 30, 0.4);
  backdrop-filter: blur(40px) saturate(200%);
  -webkit-backdrop-filter: blur(40px) saturate(200%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  /* 移除 sticky 定位，改由 flex 布局自然接管 */
  z-index: 100;
}

.main-content {
  flex: 1; /* 占据剩余全部高度 */
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 32px 24px;
  overflow-y: auto; /* 触发容器级独立滚动 */
}

/* 追加：苹果风格的沉浸式滚动条映射 */
.main-content::-webkit-scrollbar {
  width: 6px;
}
.main-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}
.main-content::-webkit-scrollbar-track {
  background: transparent;
}

.apple-control-panel {
  background: rgba(30, 30, 30, 0.5) !important;
  border-radius: 24px !important;
  margin-bottom: 40px;
  padding: 10px;
}

.macos-upload :deep(.el-upload-dragger) {
  background: rgba(0, 0, 0, 0.2);
  border: 1px dashed rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.macos-upload :deep(.el-upload-dragger:hover) {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--el-color-primary);
}

.preview-box {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 14px;
  overflow: hidden;
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 14px;
}

.re-upload-glass-tip {
  position: absolute;
  bottom: 0;
  width: 100%;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #ffffff;
  text-align: center;
  font-size: 12px;
  padding: 8px 0;
  font-weight: 500;
}

.upload-icon {
  font-size: 48px;
  color: #8e8e93;
  margin-bottom: 16px;
}

.upload-text {
  color: #ebebf5;
  font-size: 14px;
}

.upload-text span {
  color: var(--el-color-primary);
  font-weight: 500;
}

.action-col {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.macos-form :deep(.el-form-item__label) {
  color: #ebebf5;
  font-weight: 500;
}

.macos-date-picker {
  width: 100% !important;
}

.execute-btn {
  width: 100%;
  height: 50px;
  font-size: 16px;
  margin-top: 16px;
  border-radius: 16px !important;
}

.section-divider {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
}

.section-divider::before,
.section-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
}

.divider-text {
  padding: 0 16px;
  color: #8e8e93;
  font-size: 14px;
  font-weight: 500;
}

.apple-result-card {
  background: rgba(30, 30, 30, 0.4) !important;
  border-radius: 16px !important;
  margin-bottom: 24px;
  overflow: hidden;
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.apple-result-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3) !important;
}

.image-wrapper {
  position: relative;
  height: 160px;
  width: 100%;
  background: #000;
}

.result-img {
  width: 100%;
  height: 100%;
  display: block;
}

.glass-score-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 10px;
  border-radius: 10px;
  color: white;
  font-weight: 600;
  font-size: 12px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.score-high { background: rgba(50, 215, 75, 0.8); border: 1px solid rgba(50, 215, 75, 0.3); }
.score-mid { background: rgba(255, 214, 10, 0.8); border: 1px solid rgba(255, 214, 10, 0.3); color: #000; }
.score-low { background: rgba(255, 69, 58, 0.8); border: 1px solid rgba(255, 69, 58, 0.3); }

.glass-info-box {
  padding: 12px 16px;
  background: rgba(20, 20, 20, 0.6);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.main-info {
  font-weight: 600;
  color: #f5f5f7;
  font-size: 14px;
  margin-bottom: 6px;
}

.sub-info {
  font-size: 12px;
  color: #8e8e93;
  line-height: 1.5;
}

.macos-empty :deep(.el-empty__description) {
  color: #8e8e93;
}
</style>