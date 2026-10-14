<script setup>
defineProps({
  title: { type: String, default: 'Nothing here yet' },
  message: { type: String, default: 'There is no data to display.' },
})
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon">○</div>
    <strong>{{ title }}</strong>
    <span>{{ message }}</span>
    <slot />
  </div>
</template>
