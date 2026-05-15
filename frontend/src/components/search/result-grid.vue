<template>
  <SectionCard
    eyebrow="Results"
    title="检索结果"
    :description="searched ? rankingDescription : '上传查询图像并完成检索后，这里会显示相似车辆结果。'"
  >
    <template #meta>
      <span v-if="searched" class="results-meta">
        共 {{ results.length }} 条 · 耗时 {{ formatDuration(timeCost) }} · {{ sortBasisLabel }}
        <template v-if="searchMeta.deepThinkingUsed">
          · 深度思考 {{ searchMeta.rerankCandidateCount || 0 }} / {{ effectiveGallerySize || 0 }}
        </template>
      </span>
    </template>

    <div v-if="loading" class="loading-copy">
      <span class="loading-line"></span>
      <p>系统正在提取特征并计算排序，请稍候。</p>
    </div>

    <div v-else-if="results.length > 0" class="results-stack">
      <div v-if="vehicleConsensus" class="identity-insight">
        <div class="identity-copy">
          <p>System Judgement</p>
          <strong>系统判断该查询更可能属于 {{ vehicleConsensus.vehicleId }}</strong>
          <span>前 5 张结果中有 {{ vehicleConsensus.count }} 张属于该车，占比 {{ vehicleConsensus.percent }}%。</span>
        </div>
        <el-button
          type="primary"
          plain
          :loading="vehicleGalleryLoading && vehicleGalleryVisible"
          @click="openVehicleGallery"
        >
          查看该车全部图片
        </el-button>
      </div>

      <div v-if="isRerankSorting" class="rank-explain">
        <strong>深度思考排序已启用</strong>
        <p>当前列表按重排距离从低到高排列，原始相似度仍会显示，但不会严格递减。</p>
      </div>

      <div v-if="timingItems.length" class="timing-strip">
        <span v-for="item in timingItems" :key="item.label">{{ item.label }} {{ formatDuration(item.value) }}</span>
      </div>

      <div class="results-grid">
        <article
          v-for="(item, index) in results"
          :key="`${item.img_url}-${index}`"
          class="result-card"
          :class="{ podium: index < 3, reranked: isRerankSorting }"
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
              <strong v-if="isRerankSorting" class="sort-value">D {{ formatRerankDistance(item.rerank_distance) }}</strong>
              <strong v-else class="score-value" :class="`tone-${getScoreTone(item.score)}`">{{ formatScore(item.score) }}</strong>
            </div>

            <div class="score-caption">
              <span>{{ isRerankSorting ? '原始相似度' : '相似度' }}</span>
              <strong :class="`tone-${getScoreTone(item.score)}`">{{ formatScore(item.score) }}</strong>
            </div>

            <div class="score-meter" :class="`tone-${getScoreTone(item.score)}`">
              <span></span>
            </div>

            <p>摄像头：{{ item.cam_id }}</p>
            <p>采集时间：{{ formatDateTime(item.capture_time) }}</p>
          </div>
        </article>
      </div>
    </div>

    <EmptyState
      v-else-if="searched"
      eyebrow="No Match"
      title="这次没有找到匹配结果"
      description="建议更换更清晰的查询图像，或增加返回结果数量后再试一次。"
    />

    <EmptyState
      v-else
      eyebrow="Ready"
      title="等待一次新的检索"
      description="上传查询图像并完成检索后，结果会按照本次排序依据显示在这里。"
    />

    <Teleport to="body">
      <Transition name="detail-fade">
        <div
          v-if="detailVisible"
          class="result-detail-overlay"
          :class="{ 'detail-from-gallery': selectedDetailSource === 'gallery' }"
          @click.self="closeDetail"
          @wheel.stop
        >
          <section v-if="selectedResult" class="result-detail-panel" role="dialog" aria-modal="true" aria-label="结果详情">
            <button type="button" class="detail-close" aria-label="关闭结果详情" @click="closeDetail">×</button>

            <div class="detail-layout">
              <div class="detail-image-panel">
                <img :src="selectedResult.img_url" alt="selected gallery result" class="detail-image" />
                <span class="detail-rank">#{{ selectedRank + 1 }}</span>
              </div>

              <div class="detail-info">
                <p class="detail-eyebrow">Vehicle Match</p>
                <h3>{{ selectedResult.vehicle_id }}</h3>

                <div class="detail-score-grid">
                  <div class="detail-score">
                    <span>{{ detailPrimaryLabel }}</span>
                    <strong v-if="detailHasScore && isRerankSorting">D {{ formatRerankDistance(selectedResult.rerank_distance) }}</strong>
                    <strong v-else-if="detailHasScore" :class="`tone-${getScoreTone(selectedResult.score)}`">{{ formatScore(selectedResult.score) }}</strong>
                    <strong v-else>{{ detailPrimaryValue }}</strong>
                  </div>

                  <div class="detail-score">
                    <span>{{ detailSecondaryLabel }}</span>
                    <strong v-if="detailHasScore && isRerankSorting" :class="`tone-${getScoreTone(selectedResult.score)}`">{{ formatScore(selectedResult.score) }}</strong>
                    <strong v-else>{{ detailSecondaryValue }}</strong>
                  </div>
                </div>

                <div v-if="detailHasScore" class="score-meter large" :class="`tone-${getScoreTone(selectedResult.score)}`" :style="{ '--score-percent': `${scorePercent(selectedResult.score)}%` }">
                  <span></span>
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
                    <dd>{{ detailModeLabel }}</dd>
                  </div>
                  <div>
                    <dt>特征维度</dt>
                    <dd>{{ detailFeatureLabel }}</dd>
                  </div>
                  <div>
                    <dt>排序依据</dt>
                    <dd>{{ detailSortLabel }}</dd>
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
          </section>
        </div>
      </Transition>

      <Transition name="detail-fade">
        <div v-if="vehicleGalleryVisible" class="result-detail-overlay vehicle-gallery-overlay" @click.self="closeVehicleGallery" @wheel.stop>
          <section class="result-detail-panel vehicle-gallery-panel" role="dialog" aria-modal="true" aria-label="同车图库">
            <button type="button" class="detail-close" aria-label="关闭同车图库" @click="closeVehicleGallery">×</button>

            <header class="vehicle-gallery-head">
              <div>
                <p class="detail-eyebrow">Vehicle Gallery</p>
                <h3>{{ vehicleGalleryVehicleId }}</h3>
                <span>数据库中该车辆共 {{ vehicleGalleryTotal }} 张图片，当前已加载 {{ vehicleGalleryItems.length }} 张。</span>
              </div>
              <el-button plain :loading="vehicleGalleryLoading" @click="loadVehicleGallery({ reset: true })">刷新</el-button>
            </header>

            <div v-if="vehicleGalleryLoading && !vehicleGalleryItems.length" class="loading-copy gallery-loading">
              <span class="loading-line"></span>
              <p>正在按车辆编号加载图库图片。</p>
            </div>

            <div v-else-if="vehicleGalleryItems.length" class="vehicle-photo-grid">
              <article
                v-for="(item, index) in vehicleGalleryItems"
                :key="item.image_id"
                class="vehicle-photo-card"
                role="button"
                tabindex="0"
                @click="openGalleryImageDetail(item, index)"
                @keyup.enter="openGalleryImageDetail(item, index)"
              >
                <img
                  :src="item.img_url"
                  alt="same vehicle gallery image"
                  class="vehicle-photo-image"
                  loading="lazy"
                />
                <div class="vehicle-photo-meta">
                  <strong>#{{ item.image_id }}</strong>
                  <span>{{ item.cam_id }} · {{ formatDateTime(item.capture_time) }}</span>
                </div>
              </article>
            </div>

            <EmptyState
              v-else
              eyebrow="Empty"
              title="没有读取到该车辆图片"
              description="当前车辆编号在图库中没有可展示的图片记录。"
            />

            <div class="vehicle-gallery-actions">
              <span>分页加载可降低大图库下的首屏压力，图片进入视口后再请求实际文件。</span>
              <el-button
                type="primary"
                plain
                :disabled="!vehicleGalleryHasMore"
                :loading="vehicleGalleryLoading"
                @click="loadVehicleGallery()"
              >
                {{ vehicleGalleryHasMore ? '加载更多' : '已加载全部' }}
              </el-button>
            </div>
          </section>
        </div>
      </Transition>
    </Teleport>
  </SectionCard>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchVehicleImages } from '@/api/search'
import EmptyState from '@/components/base/empty-state.vue'
import SectionCard from '@/components/base/section-card.vue'
import { formatDateTime, formatDuration, getScoreTone, normalizeGalleryImages } from '@/utils/formatters'

const VEHICLE_GALLERY_PAGE_SIZE = 36

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
const selectedDetailSource = ref('results')
const selectedGalleryResult = ref(null)
const selectedGalleryIndex = ref(-1)
const vehicleGalleryVisible = ref(false)
const vehicleGalleryLoading = ref(false)
const vehicleGalleryVehicleId = ref('')
const vehicleGalleryToken = ref('')
const vehicleGalleryPage = ref(1)
const vehicleGalleryTotal = ref(0)
const vehicleGalleryHasMore = ref(false)
const vehicleGalleryItems = ref([])
const selectedResult = computed(() => selectedGalleryResult.value || props.results[selectedIndex.value] || null)
const selectedRank = computed(() => (
  selectedDetailSource.value === 'gallery'
    ? Math.max(0, selectedGalleryIndex.value)
    : Math.max(0, selectedIndex.value)
))
const isRerankSorting = computed(() => props.searchMeta?.sortBasis === 'rerank_distance' && props.searchMeta?.deepThinkingUsed)
const sortBasisLabel = computed(() => (isRerankSorting.value ? '重排距离从低到高' : '相似度从高到低'))
const effectiveGallerySize = computed(() => Number(props.searchMeta?.gallerySize || 0))
const rankingDescription = computed(() => (
  isRerankSorting.value
    ? '深度思考开启后，排序按 rerank 距离从低到高；相似度作为原始特征分数保留展示。'
    : '结果按原始特征相似度从高到低排列，点击任意图片可查看完整信息。'
))
const timingItems = computed(() => {
  const timings = props.searchMeta?.timings || {}
  const items = [
    { label: '提特征', value: timings.feature_extract_seconds },
    { label: '载入图库', value: timings.load_gallery_seconds },
    { label: '相似度', value: timings.similarity_seconds }
  ]
  if (props.searchMeta?.deepThinkingUsed) {
    items.push({ label: '深度思考', value: timings.rerank_seconds })
  }
  return items.filter((item) => Number.isFinite(Number(item.value)))
})
const vehicleConsensus = computed(() => {
  const firstFive = props.results.slice(0, 5)
  if (firstFive.length < 5) {
    return null
  }

  const counts = new Map()
  firstFive.forEach((item) => {
    const vehicleId = String(item?.vehicle_id || '').trim()
    if (!vehicleId || vehicleId === '未知' || vehicleId === '未标注车辆') {
      return
    }
    const snapshot = counts.get(vehicleId) || {
      count: 0,
      token: String(item?.vehicle_gallery_token || '').trim()
    }
    snapshot.count += 1
    if (!snapshot.token) {
      snapshot.token = String(item?.vehicle_gallery_token || '').trim()
    }
    counts.set(vehicleId, snapshot)
  })

  let bestVehicleId = ''
  let bestCount = 0
  let bestToken = ''
  counts.forEach((snapshot, vehicleId) => {
    if (snapshot.count > bestCount) {
      bestVehicleId = vehicleId
      bestCount = snapshot.count
      bestToken = snapshot.token
    }
  })

  if (bestCount < 3 || !bestToken) {
    return null
  }

  return {
    vehicleId: bestVehicleId,
    count: bestCount,
    token: bestToken,
    sampleSize: firstFive.length,
    percent: Math.round((bestCount / firstFive.length) * 100)
  }
})
const detailHasScore = computed(() => Number.isFinite(Number(selectedResult.value?.score)))
const detailPrimaryLabel = computed(() => {
  if (detailHasScore.value) {
    return isRerankSorting.value ? '当前排序依据' : '相似度'
  }
  return '图库来源'
})
const detailPrimaryValue = computed(() => (selectedDetailSource.value === 'gallery' ? '同车图库' : '--'))
const detailSecondaryLabel = computed(() => {
  if (detailHasScore.value) {
    return isRerankSorting.value ? '原始相似度' : '排序方式'
  }
  return '匹配依据'
})
const detailSecondaryValue = computed(() => {
  if (detailHasScore.value) {
    return '相似度降序'
  }
  return selectedResult.value?.vehicle_id ? '车辆编号匹配' : '--'
})
const detailModeLabel = computed(() => (
  selectedDetailSource.value === 'gallery' ? '同车图库' : (props.searchMeta?.searchMode || 'fast').toUpperCase()
))
const detailFeatureLabel = computed(() => (
  selectedDetailSource.value === 'gallery' && !detailHasScore.value ? '--' : `${props.searchMeta?.featureDim || '--'} 维`
))
const detailSortLabel = computed(() => (
  selectedDetailSource.value === 'gallery' && !detailHasScore.value ? '车辆编号匹配' : sortBasisLabel.value
))

const scorePercent = (score) => Math.max(0, Math.min(100, Number(score || 0) * 100))
const formatScore = (score) => `${scorePercent(score).toFixed(1)}%`
const formatRerankDistance = (value) => (value === null || value === undefined ? '未启用' : Number(value).toFixed(4))

const closeDetail = () => {
  detailVisible.value = false
  selectedGalleryResult.value = null
  selectedGalleryIndex.value = -1
  selectedDetailSource.value = 'results'
}

const resetVehicleGallery = () => {
  vehicleGalleryPage.value = 1
  vehicleGalleryTotal.value = 0
  vehicleGalleryHasMore.value = false
  vehicleGalleryItems.value = []
}

const loadVehicleGallery = async ({ reset = false } = {}) => {
  const targetVehicleId = vehicleGalleryVehicleId.value || vehicleConsensus.value?.vehicleId
  if (!targetVehicleId || vehicleGalleryLoading.value) {
    return
  }

  if (reset) {
    resetVehicleGallery()
  }

  vehicleGalleryLoading.value = true
  try {
    const page = reset ? 1 : vehicleGalleryPage.value + 1
    const response = await fetchVehicleImages(targetVehicleId, vehicleGalleryToken.value, {
      page,
      pageSize: VEHICLE_GALLERY_PAGE_SIZE
    })
    const payload = response.data || {}
    const items = normalizeGalleryImages(payload.items)

    vehicleGalleryPage.value = Number(payload.page || page)
    vehicleGalleryTotal.value = Number(payload.total || 0)
    vehicleGalleryHasMore.value = Boolean(payload.has_more)
    vehicleGalleryItems.value = reset ? items : [...vehicleGalleryItems.value, ...items]
  } catch {
    ElMessage.error('读取该车辆图库图片失败，请稍后重试。')
  } finally {
    vehicleGalleryLoading.value = false
  }
}

const openVehicleGallery = async () => {
  if (!vehicleConsensus.value) {
    return
  }
  if (!vehicleConsensus.value.token) {
    ElMessage.warning('当前结果未附带车辆图库访问凭证，请重新执行一次检索。')
    return
  }
  vehicleGalleryVehicleId.value = vehicleConsensus.value.vehicleId
  vehicleGalleryToken.value = vehicleConsensus.value.token
  vehicleGalleryVisible.value = true
  await loadVehicleGallery({ reset: true })
}

const closeVehicleGallery = () => {
  vehicleGalleryVisible.value = false
}

const openDetail = (item, index) => {
  if (!item) return
  selectedGalleryResult.value = null
  selectedGalleryIndex.value = -1
  selectedDetailSource.value = 'results'
  selectedIndex.value = index
  detailVisible.value = true
}

const openGalleryImageDetail = (item, index) => {
  if (!item) return
  const matchedResult = props.results.find((result) => Number(result.image_id) === Number(item.image_id))
  selectedDetailSource.value = 'gallery'
  selectedGalleryIndex.value = index
  selectedGalleryResult.value = matchedResult ? { ...item, ...matchedResult } : { ...item }
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

const handleKeydown = (event) => {
  if (event.key === 'Escape' && detailVisible.value) {
    closeDetail()
    return
  }
  if (event.key === 'Escape' && vehicleGalleryVisible.value) {
    closeVehicleGallery()
  }
}

watch([detailVisible, vehicleGalleryVisible], ([detailOpen, galleryOpen]) => {
  document.body.classList.toggle('detail-overlay-lock', detailOpen || galleryOpen)
})

watch(() => props.results, () => {
  vehicleGalleryVisible.value = false
  vehicleGalleryVehicleId.value = ''
  vehicleGalleryToken.value = ''
  resetVehicleGallery()
})

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.classList.remove('detail-overlay-lock')
})
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

.results-stack {
  display: grid;
  gap: 14px;
}

.rank-explain {
  padding: 14px 16px;
  border: 1px solid rgba(201, 100, 66, 0.24);
  border-radius: 8px;
  background: rgba(255, 250, 244, 0.50);
  box-shadow: var(--shadow-ring);
  backdrop-filter: blur(14px) saturate(1.12);
}

.rank-explain.quiet {
  border-color: var(--border-soft);
  background: rgba(255, 255, 255, 0.38);
}

.rank-explain strong {
  color: var(--text-primary);
  font-size: 14px;
}

.rank-explain p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.55;
}

.identity-insight {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  border: 1px solid rgba(201, 100, 66, 0.26);
  border-radius: 8px;
  background: rgba(250, 249, 245, 0.78);
  box-shadow: var(--shadow-ring), 0 18px 40px rgba(91, 55, 38, 0.08);
  backdrop-filter: blur(14px) saturate(1.12);
}

.identity-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.identity-copy p {
  margin: 0;
  color: var(--text-accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.identity-copy strong {
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 500;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.identity-copy span {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.45;
}

.timing-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.timing-strip span {
  padding: 6px 10px;
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.40);
  color: var(--text-secondary);
  font-family: var(--font-number);
  font-size: 12px;
  backdrop-filter: blur(12px) saturate(1.12);
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
  background: rgba(255, 255, 255, 0.46);
  box-shadow: var(--shadow-ring);
  backdrop-filter: blur(14px) saturate(1.12);
  cursor: pointer;
  animation: result-enter 0.34s ease both;
  animation-delay: calc(min(var(--entry-index), 10) * 45ms);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.result-card:hover,
.result-card:focus-visible {
  border-color: rgba(201, 100, 66, 0.34);
  background: rgba(255, 250, 244, 0.62);
  box-shadow: 0 12px 28px rgba(91, 55, 38, 0.12);
  outline: none;
}

.result-card.podium {
  box-shadow: var(--shadow-ring), 0 0 0 4px rgba(201, 100, 66, 0.06);
}

.result-card.podium.reranked {
  box-shadow: var(--shadow-ring), 0 0 0 4px rgba(100, 143, 96, 0.10), 0 0 24px rgba(201, 100, 66, 0.08);
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

.result-title-row,
.score-caption {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.score-caption span {
  color: var(--text-muted);
  font-size: 12px;
}

.score-caption strong {
  font-family: var(--font-number);
  font-size: 13px;
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

.score-value,
.sort-value {
  flex: 0 0 auto;
  font-family: var(--font-number);
  font-size: 18px;
}

.sort-value {
  color: var(--success);
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
  margin: 14px 0 4px;
}

.result-body p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
}

.result-detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 4000;
  display: grid;
  place-items: center;
  padding: 28px;
  background: rgba(20, 20, 19, 0.48);
  backdrop-filter: blur(8px);
  overscroll-behavior: contain;
}

.result-detail-overlay.detail-from-gallery {
  z-index: 4300;
}

:global(body.detail-overlay-lock) {
  overflow: hidden;
}

.result-detail-panel {
  position: relative;
  width: min(980px, 100%);
  max-height: min(86vh, 860px);
  overflow: auto;
  overscroll-behavior: contain;
  padding: 22px;
  border: 1px solid rgba(255, 250, 244, 0.38);
  border-radius: 8px;
  background: rgba(250, 249, 245, 0.98);
  box-shadow: 0 28px 80px rgba(20, 20, 19, 0.32);
  animation: detail-rise 0.22s ease both;
}

.vehicle-gallery-panel {
  width: min(1120px, 100%);
}

.detail-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 2;
  width: 34px;
  height: 34px;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.58);
  color: var(--text-secondary);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  backdrop-filter: blur(12px) saturate(1.12);
}

.detail-close:hover {
  color: var(--text-accent);
  border-color: rgba(201, 100, 66, 0.34);
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
  padding-right: 30px;
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

.vehicle-gallery-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding-right: 42px;
  margin-bottom: 18px;
}

.vehicle-gallery-head h3 {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 34px;
  font-weight: 500;
  line-height: 1.14;
  overflow-wrap: anywhere;
}

.vehicle-gallery-head span {
  display: block;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 14px;
}

.gallery-loading {
  min-height: 160px;
}

.vehicle-photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 14px;
}

.vehicle-photo-card {
  overflow: hidden;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.48);
  box-shadow: var(--shadow-ring);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.vehicle-photo-card:hover,
.vehicle-photo-card:focus-visible {
  border-color: rgba(201, 100, 66, 0.34);
  background: rgba(255, 250, 244, 0.66);
  box-shadow: 0 12px 28px rgba(91, 55, 38, 0.12);
  outline: none;
}

.vehicle-photo-image {
  display: block;
  width: 100%;
  height: 136px;
  object-fit: cover;
}

.vehicle-photo-meta {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
}

.vehicle-photo-meta strong {
  color: var(--text-primary);
  font-family: var(--font-number);
  font-size: 13px;
}

.vehicle-photo-meta span {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.vehicle-gallery-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border-soft);
}

.vehicle-gallery-actions span {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.detail-score-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.detail-score {
  padding: 14px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 250, 244, 0.46);
  backdrop-filter: blur(12px) saturate(1.12);
}

.detail-score span {
  color: var(--text-secondary);
  font-size: 13px;
}

.detail-score strong {
  display: block;
  margin-top: 2px;
  font-family: var(--font-number);
  font-size: 24px;
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
  background: rgba(255, 255, 255, 0.40);
  backdrop-filter: blur(12px) saturate(1.12);
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

.detail-fade-enter-active,
.detail-fade-leave-active {
  transition: opacity 0.18s ease;
}

.detail-fade-enter-from,
.detail-fade-leave-to {
  opacity: 0;
}

@keyframes detail-rise {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
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
  .result-detail-overlay {
    align-items: start;
    padding: 18px;
  }

  .result-detail-panel {
    max-height: calc(100vh - 36px);
    padding: 18px;
  }

  .detail-layout,
  .detail-score-grid {
    grid-template-columns: 1fr;
  }

  .identity-insight,
  .vehicle-gallery-head,
  .vehicle-gallery-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .detail-info {
    padding-right: 0;
  }

  .detail-image-panel,
  .detail-image {
    min-height: 300px;
  }

  .vehicle-photo-grid {
    grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  }
}

@media (prefers-reduced-motion: reduce) {
  .result-card,
  .vehicle-photo-card,
  .score-meter span,
  .loading-line,
  .result-image,
  .result-detail-panel {
    animation: none;
    transition: none;
  }

  .result-card:hover .result-image,
  .result-card:focus-visible .result-image {
    transform: none;
  }
}
</style>
