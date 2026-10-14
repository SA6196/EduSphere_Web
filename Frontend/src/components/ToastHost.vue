<script setup>
import { toast } from '../stores/toast.js'
</script>

<template>
  <div class="toast-host" aria-live="polite">
    <button
      v-for="item in toast.state.items"
      :key="item.id"
      class="toast-item"
      :class="`toast-${item.type}`"
      type="button"
      @click="toast.remove(item.id)"
    >
      <span class="toast-dot"></span>
      <span>{{ item.message }}</span>
    </button>
  </div>
</template>
