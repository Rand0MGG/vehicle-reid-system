<template>
  <aside class="admin-nav">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      class="nav-item"
      :class="{ active: activeKey === item.key }"
      @click="$emit('select', item.key)"
    >
      <span class="nav-index">{{ item.index }}</span>
      <span class="nav-copy">
        <strong>{{ item.label }}</strong>
        <small>{{ item.description }}</small>
      </span>
    </button>
  </aside>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => []
  },
  activeKey: {
    type: String,
    default: ''
  }
})

defineEmits(['select'])
</script>

<style scoped>
.admin-nav {
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: var(--surface-card);
  box-shadow: var(--shadow-whisper);
}

.nav-item {
  width: 100%;
  display: flex;
  gap: 14px;
  padding: 14px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.nav-item + .nav-item {
  margin-top: 8px;
}

.nav-item:hover {
  background: rgba(201, 100, 66, 0.06);
}

.nav-item.active {
  background: rgba(201, 100, 66, 0.12);
  box-shadow: 0 0 0 1px rgba(201, 100, 66, 0.18) inset;
}

.nav-index {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--text-accent);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.nav-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.nav-copy strong {
  color: var(--text-primary);
  font-size: 16px;
}

.nav-copy small {
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.5;
}

@media (max-width: 1080px) {
  .admin-nav {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 10px;
  }

  .nav-item + .nav-item {
    margin-top: 0;
  }
}

@media (max-width: 720px) {
  .admin-nav {
    grid-template-columns: 1fr;
    padding: 14px;
    border-radius: 8px;
  }
}
</style>
