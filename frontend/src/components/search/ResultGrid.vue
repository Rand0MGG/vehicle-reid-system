<template>
  <SectionCard
    eyebrow="Results"
    title="检索结果"
    :description="searched ? '结果按相似度从高到低显示，支持逐张查看原图。' : '上传查询图像并完成检索后，这里会显示相似车辆结果。'"
  >
    <template #meta>
      <span v-if="searched" class="results-meta">共 {{ results.length }} 条 · 耗时 {{ formatDuration(timeCost) }}</span>
    </template>

    <div v-if="loading" class="loading-copy">
      <p>系统正在计算相似度，请稍候。</p>
    </div>

    <div v-else-if="results.length > 0" class="results-grid">
      <article
        v-for="(item, index) in results"
        :key="`${item.img_url}-${index}`"
        class="result-card"
      >
        <div class="result-image-wrap">
          <el-image
            :src="item.img_url"
            fit="cover"
            class="result-image"
            :preview-src-list="[item.img_url]"
            preview-teleported
            hide-on-click-modal
            lazy
          />
          <span class="score-pill" :class="`tone-${getScoreTone(item.score)}`">
            {{ (item.score * 100).toFixed(1) }}%
          </span>
        </div>

        <div class="result-body">
          <h3>{{ item.vehicle_id }}</h3>
          <p>摄像头：{{ item.cam_id }}</p>
          <p>采集时间：{{ formatDateTime(item.capture_time) }}</p>
        </div>
      </article>
    </div>

    <EmptyState
      v-else-if="searched"
      eyebrow="No Match"
      title="这次没有找到匹配结果"
      description="建议更换更清晰的查询图像，或者增加返回结果数量后再试一次。"
    />

    <EmptyState
      v-else
      eyebrow="Ready"
      title="等待一次新的检索"
      description="上传查询图像并完成检索后，结果会按相似度排序显示在这里。"
    />
  </SectionCard>
</template>

<script setup>
import EmptyState from '@/components/base/EmptyState.vue'
import SectionCard from '@/components/base/SectionCard.vue'
import { formatDateTime, formatDuration, getScoreTone } from '@/utils/formatters'

defineProps({
  results: {
    type: Array,
    default: () => []
  },
  searched: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  timeCost: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
.results-meta {
  color: var(--text-muted);
  font-size: 14px;
}

.loading-copy {
  padding: 12px 4px;
}

.loading-copy p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 15px;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 18px;
}

.result-card {
  overflow: hidden;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.62);
  box-shadow: var(--shadow-ring);
}

.result-image-wrap {
  position: relative;
  height: 200px;
}

.result-image {
  width: 100%;
  height: 100%;
}

.score-pill {
  position: absolute;
  top: 12px;
  right: 12px;
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.tone-high {
  background: rgba(85, 113, 83, 0.18);
  color: #3f5e3d;
}

.tone-mid {
  background: rgba(185, 133, 59, 0.18);
  color: #8b6428;
}

.tone-low {
  background: rgba(181, 51, 51, 0.14);
  color: #9c2d2d;
}

.result-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px;
}

.result-body h3 {
  margin: 0 0 4px;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 500;
}

.result-body p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
}
</style>
