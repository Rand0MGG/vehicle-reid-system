<template>
  <SectionCard
    eyebrow="Query"
    title="上传查询图像"
    description="支持拖拽或点击上传；更换查询图像时会自动清空上一轮检索结果。"
  >
    <el-upload
      class="query-upload"
      drag
      action="#"
      :accept="accept"
      :auto-upload="false"
      :show-file-list="false"
      :on-change="handleFileChange"
    >
      <div v-if="previewUrl" class="preview-box">
        <img :src="previewUrl" alt="query preview" class="preview-image" />
        <div class="preview-overlay">
          <span>当前查询图像</span>
          <strong>{{ fileName }}</strong>
        </div>
      </div>

      <div v-else class="upload-placeholder">
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <strong>把图片拖到这里</strong>
        <p>也可以点击选择一张车辆图片，系统会基于它在图库中查找相似车辆。</p>
      </div>
    </el-upload>

    <div class="upload-toolbar">
      <div class="toolbar-copy">
        <strong>{{ fileName ? '查询图像已准备好' : '还没有选择图片' }}</strong>
        <span>
          {{
            fileName
              ? '现在可以直接开始检索，也可以重新选择一张更清晰的图片。'
              : helperMessage
          }}
        </span>
      </div>

      <el-button v-if="fileName" plain @click="$emit('reset')">清空图片</el-button>
    </div>
  </SectionCard>
</template>

<script setup>
import { UploadFilled } from '@element-plus/icons-vue'
import SectionCard from '@/components/base/section-card.vue'

defineProps({
  fileName: {
    type: String,
    default: ''
  },
  accept: {
    type: String,
    default: 'image/*'
  },
  helperMessage: {
    type: String,
    default: '建议上传主体清晰、角度稳定的车辆图像。'
  },
  previewUrl: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['file-change', 'reset'])

const handleFileChange = (uploadFile) => {
  emit('file-change', uploadFile)
}
</script>

<style scoped>
.query-upload :deep(.el-upload-dragger) {
  min-height: 300px;
  border-radius: 8px;
}

.preview-box {
  position: relative;
  min-height: 300px;
  width: 100%;
}

.preview-image {
  width: 100%;
  height: 100%;
  min-height: 300px;
  object-fit: cover;
  border-radius: 8px;
}

.preview-overlay {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 14px;
  padding: 14px 16px;
  border-radius: 8px;
  background: rgba(20, 20, 19, 0.78);
  color: var(--text-on-dark);
}

.preview-overlay span {
  display: block;
  color: var(--text-on-dark-muted);
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.preview-overlay strong {
  display: block;
  margin-top: 6px;
  font-size: 15px;
  overflow-wrap: anywhere;
}

.upload-placeholder {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  color: var(--text-secondary);
}

.upload-icon {
  color: var(--text-accent);
  font-size: 42px;
}

.upload-placeholder strong {
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 30px;
  font-weight: 500;
}

.upload-placeholder p {
  max-width: 320px;
  margin: 0;
  font-size: 15px;
  line-height: 1.55;
}

.upload-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-top: 18px;
}

.toolbar-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toolbar-copy strong {
  color: var(--text-primary);
  font-size: 15px;
}

.toolbar-copy span {
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.5;
}

@media (max-width: 720px) {
  .upload-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
