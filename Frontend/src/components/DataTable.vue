<script setup>
import { computed, ref, watch } from 'vue'
import { titleCase, formatDate, formatDateTime } from '../utils/format.js'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  empty: { type: String, default: 'No records found.' },
  searchable: { type: Boolean, default: true },
  sortable: { type: Boolean, default: true },
  pageSize: { type: Number, default: 10 },
  searchPlaceholder: { type: String, default: 'Search table…' },
})

const search = ref('')
const sortKey = ref('')
const sortDir = ref('asc')
const page = ref(1)
const pageSizeValue = ref(props.pageSize)

const resolvedColumns = computed(() => {
  if (props.columns.length) return props.columns
  const first = props.rows[0]
  return first ? Object.keys(first).map((key) => ({ key, label: titleCase(key) })) : []
})

function displayValue(row, col) {
  const raw = row?.[col.key]
  if (col.format) return col.format(raw, row)
  if (raw === null || raw === undefined || raw === '') return '—'

  const key = String(col.key)
  if (col.type === 'date' || /_date$/i.test(key)) return formatDate(raw)
  if (col.type === 'datetime' || /_at$/i.test(key)) return formatDateTime(raw)
  return raw
}
function searchText(row) {
  return resolvedColumns.value.map((col) => {
    const v = row?.[col.key]
    if (v === null || v === undefined) return ''
    return typeof v === 'object' ? JSON.stringify(v) : String(v)
  }).join(' ').toLowerCase()
}
function comparable(value) {
  if (value === null || value === undefined) return ''
  const n = Number(value)
  if (typeof value !== 'boolean' && String(value).trim() !== '' && Number.isFinite(n)) return n
  const d = Date.parse(value)
  if (typeof value === 'string' && /\d{4}-\d{2}-\d{2}/.test(value) && Number.isFinite(d)) return d
  return String(value).toLowerCase()
}

const filteredRows = computed(() => {
  const q = search.value.trim().toLowerCase()
  const list = q ? props.rows.filter((row) => searchText(row).includes(q)) : [...props.rows]
  if (!props.sortable || !sortKey.value) return list
  const key = sortKey.value
  return list.sort((a,b) => {
    const av = comparable(a?.[key]), bv = comparable(b?.[key])
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortDir.value === 'asc' ? cmp : -cmp
  })
})
const pageCount = computed(() => pageSizeValue.value > 0 ? Math.max(1, Math.ceil(filteredRows.value.length / pageSizeValue.value)) : 1)
const pagedRows = computed(() => {
  if (pageSizeValue.value <= 0) return filteredRows.value
  const start = (page.value - 1) * pageSizeValue.value
  return filteredRows.value.slice(start, start + pageSizeValue.value)
})
const rangeLabel = computed(() => {
  if (!filteredRows.value.length) return '0 records'
  if (pageSizeValue.value <= 0) return `${filteredRows.value.length} records`
  const start = (page.value - 1) * pageSizeValue.value + 1
  const end = Math.min(filteredRows.value.length, start + pageSizeValue.value - 1)
  return `${start}–${end} of ${filteredRows.value.length}`
})

function toggleSort(col) {
  if (!props.sortable || col.sortable === false) return
  if (sortKey.value === col.key) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  else { sortKey.value = col.key; sortDir.value = 'asc' }
}

watch([search, pageSizeValue], () => { page.value = 1 })
watch(pageCount, (count) => { if (page.value > count) page.value = count })
watch(() => props.rows.length, () => { if (page.value > pageCount.value) page.value = pageCount.value })
</script>

<template>
  <div v-if="rows.length" class="data-table-shell">
    <div v-if="searchable || rows.length > pageSizeValue" class="table-tools">
      <input v-if="searchable" v-model="search" class="input table-search" :placeholder="searchPlaceholder" />
      <div class="table-tools-right">
        <span class="table-range">{{ rangeLabel }}</span>
        <select v-if="rows.length > 5" v-model.number="pageSizeValue" class="select table-page-size" aria-label="Rows per page">
          <option :value="5">5 rows</option><option :value="10">10 rows</option><option :value="25">25 rows</option><option :value="50">50 rows</option><option :value="0">All</option>
        </select>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="col in resolvedColumns" :key="col.key" :class="{sortable: sortable && col.sortable !== false}" :aria-sort="sortKey===col.key ? (sortDir==='asc' ? 'ascending' : 'descending') : undefined" @click="toggleSort(col)">
              <span>{{ col.label }}</span><span v-if="sortKey===col.key" class="sort-indicator">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th v-if="$slots.actions" class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in pagedRows" :key="row.id || row.enrollment_id || row.student_id || row.offering_id || row.component_id || row.quiz_id || row.assignment_id || row.session_id || row.exam_id || index">
            <td v-for="col in resolvedColumns" :key="col.key">
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">{{ displayValue(row, col) }}</slot>
            </td>
            <td v-if="$slots.actions" class="actions-col"><slot name="actions" :row="row" /></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="pageCount > 1" class="table-pagination">
      <button class="btn btn-soft btn-sm" :disabled="page<=1" @click="page--">Previous</button>
      <span>Page {{ page }} of {{ pageCount }}</span>
      <button class="btn btn-soft btn-sm" :disabled="page>=pageCount" @click="page++">Next</button>
    </div>
  </div>
  <div v-else class="table-empty">{{ empty }}</div>
</template>
