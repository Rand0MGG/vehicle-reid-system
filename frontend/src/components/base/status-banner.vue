<template>
  <div class="status-banner" :class="`tone-${tone}`">
    <div class="status-copy">
      <strong class="status-title">{{ title }}</strong>
      <p class="status-message">{{ message }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  tone: {
    type: String,
    default: 'neutral'
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.status-banner {
  padding: 14px 16px;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.5);
}

.tone-info {
  border-color: rgba(201, 100, 66, 0.24);
  background: rgba(201, 100, 66, 0.08);
}

.tone-success {
  border-color: rgba(85, 113, 83, 0.22);
  background: rgba(85, 113, 83, 0.1);
}

.tone-warning {
  border-color: rgba(185, 133, 59, 0.22);
  background: rgba(185, 133, 59, 0.1);
}

.tone-danger {
  border-color: rgba(181, 51, 51, 0.22);
  background: rgba(181, 51, 51, 0.08);
}

.status-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
}

.status-message {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.55;
}
</style>
