<template>
  <SectionCard
    eyebrow="Model"
    :title="title"
    :description="description"
  >
    <template #meta>
      <span class="model-meta">{{ modelState.initialized ? '引擎已初始化' : '引擎尚未初始化' }}</span>
    </template>

    <div class="summary-grid">
      <StatCard label="当前运行模型" :value="modelState.current || '未读取到模型'" mono />
      <StatCard label="默认模型" :value="modelState.default || '未设置'" mono />
      <StatCard label="运行设备" :value="modelState.device || '未知'" />
    </div>

    <div class="selector-grid">
      <el-form label-position="top" class="selector-form">
        <el-form-item :label="selectionLabel">
          <el-select
            :model-value="selectedModelFile"
            filterable
            placeholder="请选择一个模型文件"
            @update:model-value="handleSelectionChange"
          >
            <el-option
              v-for="item in modelFiles"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <ActionBar align="left">
        <el-button plain :loading="loading" @click="$emit('refresh')">刷新模型列表</el-button>
        <el-button
          type="primary"
          :loading="applying"
          :disabled="!selectedModelFile || selectedModelFile === modelState.current"
          @click="$emit('apply')"
        >
          {{ applyLabel }}
        </el-button>
      </ActionBar>
    </div>

    <p class="helper-text">{{ helperText }}</p>
  </SectionCard>
</template>

<script setup>
import ActionBar from '@/components/base/ActionBar.vue'
import SectionCard from '@/components/base/SectionCard.vue'
import StatCard from '@/components/base/StatCard.vue'

defineProps({
  title: {
    type: String,
    default: '模型状态与切换'
  },
  description: {
    type: String,
    default: '所有模型信息都直接来自后端当前状态，前台只展示真实可用能力。'
  },
  selectionLabel: {
    type: String,
    default: '选择模型文件'
  },
  applyLabel: {
    type: String,
    default: '应用当前模型'
  },
  helperText: {
    type: String,
    default: '前台允许切换当前运行模型，但不会在这里暗示永久保存默认值。'
  },
  modelState: {
    type: Object,
    default: () => ({
      current: '',
      default: '',
      device: '',
      initialized: false
    })
  },
  modelFiles: {
    type: Array,
    default: () => []
  },
  selectedModelFile: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  applying: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['refresh', 'apply', 'update:selectedModelFile'])

const handleSelectionChange = (value) => {
  emit('update:selectedModelFile', value)
}
</script>

<style scoped>
.model-meta {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.58);
  color: var(--text-secondary);
  font-size: 13px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.selector-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: end;
  margin-top: 22px;
}

.selector-form {
  min-width: 0;
}

.helper-text {
  margin: 16px 0 0;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.55;
}

@media (max-width: 960px) {
  .summary-grid,
  .selector-grid {
    grid-template-columns: 1fr;
  }
}
</style>
