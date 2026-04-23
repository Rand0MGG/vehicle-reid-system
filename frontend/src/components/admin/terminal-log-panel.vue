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
import { nextTick, ref, watch } from 'vue'

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
  }
})

const bodyRef = ref(null)

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

@media (prefers-reduced-motion: reduce) {
  .terminal-line.latest,
  .terminal-shell.running .terminal-top {
    animation: none;
  }
}
</style>
