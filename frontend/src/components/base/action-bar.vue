<template>
  <div class="action-bar" :class="[`align-${align}`, { stacked }]">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  align: {
    type: String,
    default: 'left'
  },
  stacked: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.align-left {
  justify-content: flex-start;
}

.align-right {
  justify-content: flex-end;
}

.align-between {
  justify-content: space-between;
}

.stacked {
  flex-direction: column;
  align-items: stretch;
}
</style>
