<script setup>
import { computed } from 'vue'
import { displayLabel } from '../utils/format.js'

const props = defineProps({ value: { type: [String, Number], default: '' } })
const text = computed(() => displayLabel(props.value))
const tone = computed(() => {
  const v = String(props.value || '').toUpperCase()
  if (['ACTIVE','OPEN','ENROLLED','COMPLETED','PRESENT','Y','HIGH','CONFIGURED','SENT'].includes(v)) return 'positive'
  if (['ABSENT','CANCELLED','INACTIVE','N','URGENT'].includes(v)) return 'negative'
  if (['PLANNED','WAITLISTED','LATE','NORMAL','MEDIUM'].includes(v)) return 'warning'
  return 'neutral'
})
</script>

<template><span class="status-badge" :class="`status-${tone}`">{{ text }}</span></template>
