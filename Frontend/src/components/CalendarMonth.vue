<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  events: { type: Array, default: () => [] },
  title: { type: String, default: '' },
})

function toDate(value) {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}
function startMonth(date) { return new Date(date.getFullYear(), date.getMonth(), 1) }
const seed = computed(() => props.events.map((e) => toDate(e.date)).find(Boolean) || new Date())
const cursor = ref(startMonth(seed.value))
watch(seed, (d) => { cursor.value = startMonth(d) })

const monthLabel = computed(() => cursor.value.toLocaleDateString(undefined, { month:'long', year:'numeric' }))
const days = computed(() => {
  const year = cursor.value.getFullYear(), month = cursor.value.getMonth()
  const first = new Date(year, month, 1)
  const offset = first.getDay()
  const total = new Date(year, month + 1, 0).getDate()
  const cells = []
  for (let i = 0; i < offset; i++) cells.push({ blank:true, key:`b${i}` })
  for (let day = 1; day <= total; day++) {
    const date = new Date(year, month, day)
    const key = `${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`
    const events = props.events.filter((event) => {
      const d = toDate(event.date)
      return d && d.getFullYear()===year && d.getMonth()===month && d.getDate()===day
    })
    cells.push({ blank:false, day, key, date, events })
  }
  return cells
})
function move(delta) { cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth()+delta, 1) }
</script>

<template>
  <div class="calendar-card">
    <div class="calendar-head">
      <div><strong>{{ title || 'Calendar' }}</strong><span>{{ monthLabel }}</span></div>
      <div class="calendar-nav"><button class="btn btn-soft btn-sm" @click="move(-1)">‹</button><button class="btn btn-soft btn-sm" @click="move(1)">›</button></div>
    </div>
    <div class="calendar-weekdays"><span v-for="d in ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']" :key="d">{{ d }}</span></div>
    <div class="calendar-grid">
      <div v-for="cell in days" :key="cell.key" class="calendar-day" :class="{blank:cell.blank, 'has-event':cell.events?.length}">
        <template v-if="!cell.blank">
          <span class="calendar-number">{{ cell.day }}</span>
          <div class="calendar-events">
            <div v-for="(event, i) in cell.events.slice(0,3)" :key="event.key || i" class="calendar-event" :title="event.detail || event.label">
              {{ event.label }}
            </div>
            <span v-if="cell.events.length > 3" class="calendar-more">+{{ cell.events.length - 3 }} more</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
