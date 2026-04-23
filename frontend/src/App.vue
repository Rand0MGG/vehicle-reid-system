<template>
  <router-view />
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'

let frameId = 0

const canUseMouseAura = () => {
  if (typeof window === 'undefined') return false
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const finePointer = window.matchMedia('(pointer: fine)').matches
  return !reducedMotion && finePointer
}

const handlePointerMove = (event) => {
  if (!canUseMouseAura()) return
  if (frameId) cancelAnimationFrame(frameId)
  frameId = requestAnimationFrame(() => {
    document.documentElement.style.setProperty('--mouse-x', `${event.clientX}px`)
    document.documentElement.style.setProperty('--mouse-y', `${event.clientY}px`)
  })
}

onMounted(() => {
  window.addEventListener('pointermove', handlePointerMove, { passive: true })
})

onBeforeUnmount(() => {
  if (frameId) cancelAnimationFrame(frameId)
  window.removeEventListener('pointermove', handlePointerMove)
})
</script>
