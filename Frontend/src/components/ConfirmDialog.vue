<script setup>
const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: 'Confirm action' },
  message: { type: String, default: 'Are you sure?' },
  confirmLabel: { type: String, default: 'Confirm' },
  cancelLabel: { type: String, default: 'Cancel' },
  tone: { type: String, default: 'primary' },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm', 'cancel'])
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="dialog-backdrop" @click.self="!busy && emit('cancel')">
      <div class="dialog-card" role="dialog" aria-modal="true" :aria-label="title">
        <div class="dialog-icon" :class="`dialog-${tone}`">!</div>
        <h3>{{ title }}</h3>
        <p>{{ message }}</p>
        <div class="dialog-actions">
          <button class="btn btn-soft" :disabled="busy" @click="emit('cancel')">{{ cancelLabel }}</button>
          <button :class="['btn', tone === 'danger' ? 'btn-danger' : 'btn-primary']" :disabled="busy" @click="emit('confirm')">
            {{ busy ? 'Working…' : confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
