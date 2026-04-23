<template>
  <div class="terminal-shell" :class="{ running: isRunning }">
    <div class="terminal-top">
      <div class="lights">
        <span class="light red"></span>
        <span class="light yellow"></span>
        <span class="light green"></span>
      </div>
      <span>{{ title }}</span>
    </div>

    <div v-if="hasProgress" class="task-progress">
      <div class="task-progress-main">
        <div>
          <strong>{{ status.message || (isRunning ? '任务运行中' : '最近任务') }}</strong>
          <p>{{ status.processed || 0 }} / {{ status.total || 0 }} · 新增/成功 {{ status.created || 0 }} · 跳过 {{ status.skipped || 0 }} · 失败 {{ status.failed || 0 }}</p>
        </div>
        <span>{{ normalizedProgress.toFixed(1) }}%</span>
      </div>

      <div class="progress-track" :class="{ running: isRunning }">
        <span :style="{ width: `${normalizedProgress}%` }"></span>
      </div>

      <div class="task-metrics">
        <span>耗时 {{ formatDuration(status.elapsed_seconds) }}</span>
        <span v-if="status.duration_seconds !== null && status.duration_seconds !== undefined">总用时 {{ formatDuration(status.duration_seconds) }}</span>
        <span v-if="isRunning && status.estimated_remaining_seconds !== null && status.estimated_remaining_seconds !== undefined">预计剩余 {{ formatDuration(status.estimated_remaining_seconds) }}</span>
        <span>速度 {{ formatRate(status.items_per_second) }}</span>
      </div>
    </div>

    <div ref="bodyRef" class="terminal-body">
      <div v-if="logs.length === 0" class="terminal-line terminal-placeholder">
        等待新的处理日志输出。
      </div>

      <div v-for="(log, index) in logs" :key="`${index}-${log}`" class="terminal-line" :class="{ latest: index === logs.length - 1 }">
        {{ log }}
      </div>

      <div v-if="isRunning" class="terminal-line terminal-cursor">...</div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { formatDuration } from '@/utils/formatters'

const props = defineProps({
  title: {
    type: String,
    default: '图库处理日志'
  },
  logs: {
    type: Array,
    default: () => []
  },
  isRunning: {
    type: Boolean,
    default: false
  },
  status: {
    type: Object,
    default: () => ({})
  }
})

const bodyRef = ref(null)
const hasProgress = computed(() => Number(props.status?.total || 0) > 0 || props.isRunning)
const normalizedProgress = computed(() => {
  const progress = Number(props.status?.progress_percent ?? 0)
  if (Number.isFinite(progress)) {
    return Math.max(0, Math.min(100, progress))
  }
  const total = Number(props.status?.total || 0)
  const processed = Number(props.status?.processed || 0)
  return total > 0 ? Math.max(0, Math.min(100, processed / total * 100)) : 0
})

const formatRate = (value) => {
  const rate = Number(value)
  if (!Number.isFinite(rate) || rate <= 0) return '-- 项/秒'
  if (rate < 10) return `${rate.toFixed(2)} 项/秒`
  return `${rate.toFixed(1)} 项/秒`
}

const scrollToBottom = async () => {
  await nextTick()

  if (bodyRef.value) {
    bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  }
}

watch(
  () => [props.logs.length, props.isRunning],
  () => {
    scrollToBottom()
  },
  { immediate: true }
)

defineExpose({
  scrollToBottom
})
</script>

<style scoped>
.terminal-shell {
  overflow: hidden;
  border: 1px solid var(--surface-dark-border);
  border-radius: 8px;
  background: var(--surface-dark);
}

.terminal-shell.running {
  box-shadow: 0 0 0 1px rgba(201, 100, 66, 0.28), 0 12px 30px rgba(20, 20, 19, 0.16);
}

.terminal-top {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--surface-dark-border);
  background: #242320;
  color: var(--text-on-dark-muted);
  font-size: 13px;
}

.terminal-shell.running .terminal-top {
  background:
    linear-gradient(90deg, rgba(201, 100, 66, 0.18), transparent 34%, rgba(201, 100, 66, 0.18) 68%, transparent),
    #242320;
  background-size: 180% 100%;
  animation: terminal-flow 1.6s linear infinite;
}

.lights {
  display: flex;
  gap: 8px;
}

.light {
  width: 11px;
  height: 11px;
  border-radius: 999px;
}

.light.red {
  background: #c66464;
}

.light.yellow {
  background: #d1a256;
}

.light.green {
  background: #648f60;
}

.task-progress {
  display: grid;
  gap: 10px;
  padding: 14px 16px 16px;
  border-bottom: 1px solid var(--surface-dark-border);
  background: rgba(255, 250, 244, 0.06);
}

.task-progress-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.task-progress-main strong {
  color: var(--text-on-dark);
  font-size: 14px;
  font-weight: 600;
}

.task-progress-main p,
.task-metrics {
  margin: 4px 0 0;
  color: var(--text-on-dark-muted);
  font-family: var(--font-number);
  font-size: 12px;
}

.task-progress-main > span {
  color: #f0b29a;
  font-family: var(--font-number);
  font-weight: 700;
}

.progress-track {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 250, 244, 0.12);
}

.progress-track span {
  display: block;
  width: 0;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #d97757, #f0b29a, #c96442);
  background-size: 180% 100%;
  transition: width 0.28s ease;
}

.progress-track.running span {
  animation: progress-shimmer 1.35s linear infinite;
}

.task-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.terminal-body {
  height: 420px;
  overflow: auto;
  padding: 18px;
  color: var(--text-on-dark);
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.7;
}

.terminal-line + .terminal-line {
  margin-top: 4px;
}

.terminal-placeholder,
.terminal-cursor {
  color: var(--text-on-dark-muted);
}

.terminal-line.latest {
  animation: log-flash 0.72s ease both;
}

@keyframes log-flash {
  0% {
    color: #fffaf5;
    text-shadow: 0 0 12px rgba(217, 119, 87, 0.5);
  }
  100% {
    color: var(--text-on-dark);
    text-shadow: none;
  }
}

@keyframes terminal-flow {
  from {
    background-position: 0 0;
  }
  to {
    background-position: 180% 0;
  }
}

@keyframes progress-shimmer {
  from {
    background-position: 0 0;
  }
  to {
    background-position: 180% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .terminal-line.latest,
  .terminal-shell.running .terminal-top,
  .progress-track.running span {
    animation: none;
  }

  .progress-track span {
    transition: none;
  }
}
</style>
