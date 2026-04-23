<template>
  <SectionCard
    eyebrow="Results"
    title="检索结果"
    :description="searched ? '结果按当前模式排序，点击任意图片可查看完整信息。' : '上传查询图像并完成检索后，这里会显示相似车辆结果。'"
  >
    <template #meta>
      <span v-if="searched" class="results-meta">
        共 {{ results.length }} 条 · 耗时 {{ formatDuration(timeCost) }}
        <template v-if="searchMeta.deepThinkingUsed">
          · 深度思考 {{ searchMeta.rerankCandidateCount || 0 }} / {{ searchMeta.gallerySize || 0 }}
        </template>
      </span>
    </template>

    <div v-if="loading" class="loading-copy">
      <span class="loading-line"></span>
      <p>系统正在计算相似度，请稍候。</p>
    </div>

    <div v-else-if="results.length > 0" class="results-grid">
      <article
        v-for="(item, index) in results"
        :key="`${item.img_url}-${index}`"
        class="result-card"
        :class="{ podium: index < 3 }"
        :style="{ '--entry-index': index, '--score-percent': `${scorePercent(item.score)}%` }"
        role="button"
        tabindex="0"
        @click="openDetail(item, index)"
        @keyup.enter="openDetail(item, index)"
      >
        <div class="result-image-wrap">
          <img :src="item.img_url" alt="gallery result" class="result-image" loading="lazy" />
          <span class="rank-badge" :class="{ podium: index < 3 }">#{{ index + 1 }}</span>
        </div>

        <div class="result-body">
          <div class="result-title-row">
            <h3>{{ item.vehicle_id }}</h3>
            <strong class="score-value" :class="`tone-${getScoreTone(item.score)}`">{{ formatScore(item.score) }}</strong>
          </div>

          <div class="score-meter" :class="`tone-${getScoreTone(item.score)}`">
            <span></span>
          </div>

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

    <el-dialog v-model="detailVisible" title="结果详情" width="980px" class="result-detail-dialog">
      <div v-if="selectedResult" class="detail-layout">
        <div class="detail-image-panel">
          <img :src="selectedResult.img_url" alt="selected gallery result" class="detail-image" />
          <span class="detail-rank">#{{ selectedRank + 1 }}</span>
        </div>

        <div class="detail-info">
          <p class="detail-eyebrow">Vehicle Match</p>
          <h3>{{ selectedResult.vehicle_id }}</h3>

          <div class="detail-score">
            <span>相似度</span>
            <strong :class="`tone-${getScoreTone(selectedResult.score)}`">{{ formatScore(selectedResult.score) }}</strong>
            <div class="score-meter large" :class="`tone-${getScoreTone(selectedResult.score)}`" :style="{ '--score-percent': `${scorePercent(selectedResult.score)}%` }">
              <span></span>
            </div>
          </div>

          <dl class="detail-list">
            <div>
              <dt>图片 ID</dt>
              <dd>{{ selectedResult.image_id || '未知' }}</dd>
            </div>
            <div>
              <dt>摄像头</dt>
              <dd>{{ selectedResult.cam_id }}</dd>
            </div>
            <div>
              <dt>采集时间</dt>
              <dd>{{ formatDateTime(selectedResult.capture_time) }}</dd>
            </div>
            <div>
              <dt>检索模式</dt>
              <dd>{{ (searchMeta.searchMode || 'fast').toUpperCase() }}</dd>
            </div>
            <div>
              <dt>特征维度</dt>
              <dd>{{ searchMeta.featureDim || '--' }} 维</dd>
            </div>
            <div>
              <dt>Rerank 距离</dt>
              <dd>{{ formatRerankDistance(selectedResult.rerank_distance) }}</dd>
            </div>
          </dl>

          <div class="path-box">
            <span>图片路径</span>
            <code>{{ selectedResult.img_path || '暂无路径' }}</code>
            <el-button size="small" plain :disabled="!selectedResult.img_path" @click="copyPath(selectedResult.img_path)">复制路径</el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </SectionCard>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import EmptyState from '@/components/base/empty-state.vue'
import SectionCard from '@/components/base/section-card.vue'
import { formatDateTime, formatDuration, getScoreTone } from '@/utils/formatters'

const props = defineProps({
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
  },
  searchMeta: {
    type: Object,
    default: () => ({})
  }
})

const detailVisible = ref(false)
const selectedIndex = ref(-1)
const selectedResult = computed(() => props.results[selectedIndex.value] || null)
const selectedRank = computed(() => Math.max(0, selectedIndex.value))

const scorePercent = (score) => Math.max(0, Math.min(100, Number(score || 0) * 100))
const formatScore = (score) => `${scorePercent(score).toFixed(1)}%`
const formatRerankDistance = (value) => (value === null || value === undefined ? '未启用' : Number(value).toFixed(4))

const openDetail = (item, index) => {
  if (!item) return
  selectedIndex.value = index
  detailVisible.value = true
}

const copyPath = async (path) => {
  if (!path) return
  try {
    await navigator.clipboard.writeText(path)
    ElMessage.success('图片路径已复制。')
  } catch {
    ElMessage.warning('当前浏览器不允许直接复制，请手动选择路径。')
  }
}
</script>

<style scoped>
.results-meta {
  color: var(--text-muted);
  font-size: 14px;
}

.loading-copy {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
}

.loading-copy p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 15px;
}

.loading-line {
  width: 72px;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(201, 100, 66, 0.12), rgba(201, 100, 66, 0.86), rgba(201, 100, 66, 0.12));
  animation: loading-breathe 1.1s ease-in-out infinite;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 18px;
}

.result-card {
  overflow: hidden;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.62);
  box-shadow: var(--shadow-ring);
  cursor: pointer;
  animation: result-enter 0.34s ease both;
  animation-delay: calc(min(var(--entry-index), 10) * 45ms);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.result-card:hover,
.result-card:focus-visible {
  border-color: rgba(201, 100, 66, 0.34);
  background: rgba(255, 250, 244, 0.78);
  box-shadow: 0 12px 28px rgba(91, 55, 38, 0.12);
  outline: none;
}

.result-card.podium {
  box-shadow: var(--shadow-ring), 0 0 0 4px rgba(201, 100, 66, 0.06);
}

.result-image-wrap {
  position: relative;
  height: 200px;
  overflow: hidden;
}

.result-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.28s ease;
}

.result-card:hover .result-image,
.result-card:focus-visible .result-image {
  transform: scale(1.035);
}

.rank-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 42px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(255, 250, 244, 0.44);
  border-radius: 999px;
  background: rgba(20, 20, 19, 0.72);
  color: #fffaf5;
  font-family: var(--font-number);
  font-size: 13px;
  font-weight: 700;
}

.rank-badge.podium {
  background: linear-gradient(180deg, rgba(201, 100, 66, 0.92), rgba(167, 95, 66, 0.92));
}

.result-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
}

.result-title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.result-body h3 {
  min-width: 0;
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 500;
  overflow-wrap: anywhere;
}

.score-value {
  flex: 0 0 auto;
  font-family: var(--font-number);
  font-size: 18px;
}

.tone-high {
  color: #3f5e3d;
}

.tone-mid {
  color: #8b6428;
}

.tone-low {
  color: #9c2d2d;
}

.score-meter {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(231, 226, 215, 0.92);
}

.score-meter span {
  display: block;
  width: var(--score-percent);
  height: 100%;
  border-radius: inherit;
  animation: score-fill 0.62s ease both;
}

.score-meter.tone-high span {
  background: linear-gradient(90deg, #648f60, #557153);
}

.score-meter.tone-mid span {
  background: linear-gradient(90deg, #d1a256, #b9853b);
}

.score-meter.tone-low span {
  background: linear-gradient(90deg, #cf7770, #b53333);
}

.score-meter.large {
  height: 12px;
  margin-top: 8px;
}

.result-body p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: 22px;
}

.detail-image-panel {
  position: relative;
  min-height: 420px;
  overflow: hidden;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(20, 20, 19, 0.05);
}

.detail-image {
  width: 100%;
  height: 100%;
  min-height: 420px;
  object-fit: contain;
}

.detail-rank {
  position: absolute;
  top: 14px;
  left: 14px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(20, 20, 19, 0.74);
  color: #fffaf5;
  font-family: var(--font-number);
  font-weight: 700;
}

.detail-info {
  min-width: 0;
}

.detail-eyebrow {
  margin: 0 0 8px;
  color: var(--text-accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.detail-info h3 {
  margin: 0 0 18px;
  font-family: var(--font-serif);
  font-size: 34px;
  font-weight: 500;
}

.detail-score {
  padding: 14px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 250, 244, 0.68);
}

.detail-score span {
  color: var(--text-secondary);
  font-size: 13px;
}

.detail-score strong {
  display: block;
  margin-top: 2px;
  font-family: var(--font-number);
  font-size: 34px;
  line-height: 1.1;
}

.detail-list {
  display: grid;
  gap: 10px;
  margin: 16px 0;
}

.detail-list div {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-soft);
}

.detail-list dt {
  color: var(--text-muted);
  font-size: 13px;
}

.detail-list dd {
  min-width: 0;
  margin: 0;
  color: var(--text-primary);
  font-size: 14px;
  overflow-wrap: anywhere;
}

.path-box {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.54);
}

.path-box span {
  color: var(--text-muted);
  font-size: 13px;
}

.path-box code {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

@keyframes result-enter {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes score-fill {
  from {
    width: 0;
  }
}

@keyframes loading-breathe {
  0%,
  100% {
    opacity: 0.45;
  }
  50% {
    opacity: 1;
  }
}

@media (max-width: 820px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .detail-image-panel,
  .detail-image {
    min-height: 300px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .result-card,
  .score-meter span,
  .loading-line,
  .result-image {
    animation: none;
    transition: none;
  }

  .result-card:hover .result-image,
  .result-card:focus-visible .result-image {
    transform: none;
  }
}
</style>
