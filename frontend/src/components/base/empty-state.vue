<template>
  <div class="empty-state" :class="[`align-${align}`]">
    <p v-if="eyebrow" class="empty-eyebrow">{{ eyebrow }}</p>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-description">{{ description }}</p>
    <div v-if="$slots.default" class="empty-actions">
      <slot />
    </div>
  </div>
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
  },
  align: {
    type: String,
    default: 'center'
  }
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px 4px;
}

.align-center {
  align-items: center;
  text-align: center;
}

.align-left {
  align-items: flex-start;
  text-align: left;
}

.empty-eyebrow {
  margin: 0;
  color: var(--text-accent);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.empty-title {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 500;
  line-height: 1.18;
}

.empty-description {
  max-width: 620px;
  margin: 0;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.6;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
}
</style>
