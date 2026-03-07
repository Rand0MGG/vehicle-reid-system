<template>
  <div class="search-container">
    <div class="header">
      <h2>🔍 车辆重识别检索系统 (Vehicle ReID)</h2>
      <p>上传目标车辆图片，在底库中检索同车轨迹</p>
    </div>

    <el-card class="control-panel">
      <el-row :gutter="20">
        <el-col :span="10">
          <el-upload
            class="upload-demo"
            drag
            action="#"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleFileChange"
          >
            <div v-if="previewUrl" class="preview-box">
              <img :src="previewUrl" class="preview-img" />
              <div class="re-upload-tip">点击或拖拽替换图片</div>
            </div>
            <div v-else class="upload-placeholder">
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                拖拽图片到此处 或 <em>点击上传</em>
              </div>
            </div>
          </el-upload>
        </el-col>

        <el-col :span="14" class="action-col">
          <el-form label-position="top">
            <el-form-item label="期望结果数量 (Top-K)">
              <el-slider v-model="topK" :min="1" :max="20" show-input />
            </el-form-item>
            
            <el-form-item label="时间范围 (暂未启用)">
              <el-date-picker
                v-model="dateRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                disabled
              />
            </el-form-item>

            <div class="btn-group">
              <el-button 
                type="primary" 
                size="large" 
                :loading="loading" 
                @click="handleSearch"
                style="width: 100%;"
              >
                {{ loading ? '正在AI推理中...' : '🚀 开始检索' }}
              </el-button>
            </div>
          </el-form>
        </el-col>
      </el-row>
    </el-card>

    <div class="results-section" v-if="results.length > 0">
      <el-divider content-position="left">检索结果 (耗时: {{ timeCost }}s)</el-divider>
      
      <el-row :gutter="20">
        <el-col 
          v-for="(item, index) in results" 
          :key="index" 
          :xs="12" :sm="8" :md="6" :lg="4"
        >
          <el-card :body-style="{ padding: '0px' }" class="result-card">
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
              <div class="score-badge" :class="getScoreClass(item.score)">
                {{ (item.score * 100).toFixed(1) }}%
              </div>
            </div>
            <div class="info-box">
              <div class="main-info">ID: {{ item.vehicle_id }}</div>
              <div class="sub-info">📷 {{ item.cam_id }}</div>
              <div class="sub-info">🕒 {{ formatTime(item.capture_time) }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    
    <el-empty v-else-if="searched" description="未找到相似车辆" />
    <el-button type="danger" @click="handleLogout">退出系统</el-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { searchVehicle } from '@/api/search'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

// 状态定义
const loading = ref(false)
const searched = ref(false)
const topK = ref(10)
const dateRange = ref([])
const file = ref(null)
const previewUrl = ref('')
const results = ref([])
const timeCost = ref(0)
const router = useRouter()

const handleLogout = () => {
  localStorage.removeItem('access_token')
  ElMessage.success('已安全退出系统')
  router.push('/login')
}

// 1. 处理文件选择
const handleFileChange = (uploadFile) => {
  file.value = uploadFile.raw
  previewUrl.value = URL.createObjectURL(uploadFile.raw)
  searched.value = false
  results.value = []
}

// 2. 触发检索
const handleSearch = async () => {
  if (!file.value) {
    ElMessage.warning('请先上传一张图片！')
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
    
    ElMessage.success(`检索完成，耗时 ${data.time_cost}秒`)
    
  } catch (error) {
    console.error(error)
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
  if (!timeStr) return 'Unknown'
  return timeStr.replace('T', ' ')
}
</script>

<style scoped>
.search-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h2 {
  color: #303133;
  margin-bottom: 10px;
  font-weight: 600;
}

.header p {
  color: #606266;
  font-size: 14px;
}

.control-panel {
  margin-bottom: 30px;
}

.preview-box {
  position: relative;
  width: 100%;
  height: 200px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px dashed #d9d9d9;
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background-color: #f5f7fa;
}

.re-upload-tip {
  position: absolute;
  bottom: 0;
  width: 100%;
  background: rgba(0,0,0,0.5);
  color: white;
  text-align: center;
  font-size: 12px;
  padding: 4px 0;
}

.action-col {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.result-card {
  margin-bottom: 20px;
  transition: transform 0.2s;
}

.result-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.image-wrapper {
  position: relative;
  height: 150px;
  background: #000;
}

.result-img {
  width: 100%;
  height: 100%;
  display: block;
}

.score-badge {
  position: absolute;
  top: 5px;
  right: 5px;
  padding: 2px 6px;
  border-radius: 4px;
  color: white;
  font-weight: bold;
  font-size: 12px;
}

.score-high { background-color: #67C23A; }
.score-mid { background-color: #E6A23C; }
.score-low { background-color: #F56C6C; }

.info-box {
  padding: 10px;
}

.main-info {
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.sub-info {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
</style>