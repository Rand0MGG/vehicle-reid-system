<template>
  <article class="stat-card" :class="[`tone-${tone}`, { mono, number, text }]">
    <p class="stat-label">{{ label }}</p>
    <strong class="stat-value" :title="value">{{ value }}</strong>
    <p v-if="hint" class="stat-hint">{{ hint }}</p>
  </article>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    default: ''
  },
  value: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  },
  tone: {
    type: String,
    default: 'default'
  },
  mono: {
    type: Boolean,
    default: false
  },
  number: {
    type: Boolean,
    default: false
  },
  text: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.stat-card {
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.42);
  box-shadow: var(--shadow-ring);
  backdrop-filter: blur(14px) saturate(1.14);
}

.tone-strong {
  background: var(--surface-strong);
}

.tone-dark {
  background: var(--surface-dark);
  border-color: var(--surface-dark-border);
  box-shadow: none;
}

.tone-dark .stat-label,
.tone-dark .stat-hint {
  color: var(--text-on-dark-muted);
}

.tone-dark .stat-value {
  color: var(--text-on-dark);
}

.stat-label {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.stat-value {
  display: block;
  margin-top: 10px;
  color: var(--text-primary);
  font-family: var(--font-number);
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 500;
  line-height: 1.24;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.mono .stat-value {
  font-family: var(--font-mono);
  font-size: 18px;
}

.text .stat-value {
  font-family: var(--font-sans);
  font-size: 18px;
  font-weight: 700;
}

.number .stat-value {
  font-family: var(--font-number);
}

.stat-hint {
  margin: 10px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.55;
}
</style>
