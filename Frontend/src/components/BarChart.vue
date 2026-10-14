<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  max: { type: Number, default: 0 },
  suffix: { type: String, default: '' },
  empty: { type: String, default: 'No chart data available.' },
})

const resolvedMax = computed(() => {
  if (props.max > 0) return props.max
  const values = props.items.map((x) => Number(x.value)).filter(Number.isFinite)
  return Math.max(1, ...values)
})
function width(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return 0
  return Math.max(0, Math.min(100, (n / resolvedMax.value) * 100))
}
function display(value) {
  const n = Number(value)
  return Number.isFinite(n) ? `${Math.round(n * 100) / 100}${props.suffix}` : '—'
}
</script>

<template>
  <div v-if="items.length" class="bar-chart">
    <div v-for="(item, i) in items" :key="item.key || item.label || i" class="bar-chart-row">
      <div class="bar-chart-label" :title="[item.label, item.hint].filter(Boolean).join(' · ')"><strong>{{ item.label }}</strong><span v-if="item.hint">{{ item.hint }}</span></div>
      <div class="bar-chart-track" :title="`${item.label}: ${display(item.value)}`"><div class="bar-chart-fill" :style="{ width: `${width(item.value)}%` }"></div></div>
      <div class="bar-chart-value">{{ display(item.value) }}</div>
    </div>
  </div>
  <div v-else class="table-empty">{{ empty }}</div>
</template>
