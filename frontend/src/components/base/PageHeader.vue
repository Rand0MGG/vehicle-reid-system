<template>
  <header class="page-header">
    <div class="page-copy">
      <p v-if="eyebrow" class="page-eyebrow">{{ eyebrow }}</p>
      <h1 class="page-title">{{ title }}</h1>
      <p v-if="description" class="page-description">{{ description }}</p>
    </div>

    <div v-if="$slots.meta || $slots.actions" class="page-aside">
      <div v-if="$slots.meta" class="page-meta">
        <slot name="meta" />
      </div>

      <div v-if="$slots.actions" class="page-actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 32px;
  border: 1px solid var(--border-soft);
  border-radius: 32px;
  background: var(--surface-panel);
  box-shadow: var(--shadow-whisper);
}

.page-copy {
  min-width: 0;
}

.page-eyebrow {
  margin: 0 0 12px;
  color: var(--text-accent);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.page-title {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: clamp(40px, 5vw, 64px);
  font-weight: 500;
  line-height: 1.08;
}

.page-description {
  max-width: 820px;
  margin: 16px 0 0;
  color: var(--text-secondary);
  font-size: 18px;
  line-height: 1.6;
}

.page-aside {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 260px;
}

.page-meta,
.page-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 960px) {
  .page-header {
    padding: 24px;
    border-radius: 24px;
    flex-direction: column;
  }

  .page-aside {
    min-width: 0;
    width: 100%;
  }

  .page-meta,
  .page-actions {
    justify-content: flex-start;
  }
}
</style>
