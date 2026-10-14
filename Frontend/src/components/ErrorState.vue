<script setup>
const props = defineProps({
  title: { type: String, default: 'Unable to load this page' },
  message: { type: String, default: 'Something went wrong while completing this request.' },
  retryable: { type: Boolean, default: false },
  showBack: { type: Boolean, default: true },
  retryLabel: { type: String, default: 'Try again' },
  backLabel: { type: String, default: 'Go back' },
})

defineEmits(['retry', 'back'])
</script>

<template>
  <section class="error-state" role="alert" aria-live="polite">
    <div class="error-state-icon">!</div>
    <div class="error-state-copy">
      <h2>{{ title }}</h2>
      <p>{{ message }}</p>
      <div class="error-state-actions">
        <button v-if="retryable" class="btn btn-primary" type="button" @click="$emit('retry')">{{ retryLabel }}</button>
        <button v-if="showBack" class="btn btn-soft" type="button" @click="$emit('back')">{{ backLabel }}</button>
      </div>
    </div>
  </section>
</template>
