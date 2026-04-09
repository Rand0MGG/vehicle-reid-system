<template>
  <div class="terminal-shell">
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

      <div v-for="(log, index) in logs" :key="`${index}-${log}`" class="terminal-line">
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
  border-radius: 22px;
  background: var(--surface-dark);
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

.terminal-placeholder {
  color: var(--text-on-dark-muted);
}

.terminal-cursor {
  color: var(--text-on-dark-muted);
}
</style>
