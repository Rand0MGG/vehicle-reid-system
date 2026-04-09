<template>
  <section class="section-card" :class="[`tone-${tone}`, { compact }]">
    <header v-if="showHeader" class="section-header">
      <div class="section-copy">
        <p v-if="eyebrow" class="section-eyebrow">{{ eyebrow }}</p>
        <h2 v-if="title" class="section-title">{{ title }}</h2>
        <p v-if="description" class="section-description">{{ description }}</p>
      </div>

      <div v-if="$slots.meta || $slots.actions" class="section-aside">
        <div v-if="$slots.meta" class="section-meta">
          <slot name="meta" />
        </div>

        <div v-if="$slots.actions" class="section-actions">
          <slot name="actions" />
        </div>
      </div>
    </header>

    <div class="section-body">
      <slot />
    </div>
  </section>
</template>

<script setup>
import { computed, useSlots } from 'vue'

const props = defineProps({
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
  },
  tone: {
    type: String,
    default: 'default'
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const slots = useSlots()

const showHeader = computed(() => {
  return Boolean(props.eyebrow || props.title || props.description || slots.meta || slots.actions)
})
</script>

<style scoped>
.section-card {
  padding: 28px;
  border: 1px solid var(--border-soft);
  border-radius: 28px;
  background: var(--surface-card);
  box-shadow: var(--shadow-whisper);
}

.section-card.compact {
  padding: 22px;
  border-radius: 24px;
}

.tone-muted {
  background: rgba(255, 255, 255, 0.56);
}

.tone-contrast {
  background: var(--surface-strong);
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.section-copy {
  min-width: 0;
}

.section-eyebrow {
  margin: 0 0 10px;
  color: var(--text-accent);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.section-title {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: clamp(28px, 3.5vw, 38px);
  font-weight: 500;
  line-height: 1.12;
}

.section-description {
  max-width: 760px;
  margin: 10px 0 0;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.6;
}

.section-aside {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-end;
}

.section-meta,
.section-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.section-body {
  margin-top: 22px;
}

@media (max-width: 860px) {
  .section-card,
  .section-card.compact {
    padding: 22px;
    border-radius: 24px;
  }

  .section-header {
    flex-direction: column;
  }

  .section-aside,
  .section-meta,
  .section-actions {
    align-items: flex-start;
    justify-content: flex-start;
  }
}
</style>
