<script setup>
import { computed, onMounted, ref } from 'vue'
import AppShell from '../components/AppShell.vue'
import SectionCard from '../components/SectionCard.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import LoadingState from '../components/LoadingState.vue'
import { api } from '../services/api.js'
import { auth } from '../stores/auth.js'
import { toast } from '../stores/toast.js'

const offerings = ref([])
const query = ref('')
const error = ref('')
const loading = ref(true)
const enrollingId = ref(null)
const selectedOffering = ref(null)
const selectedDropOffering = ref(null)
const droppingId = ref(null)
const studentCourses = ref([])
const role = computed(() => auth.state.user?.role)
const enrollmentByOffering = computed(() => new Map(studentCourses.value.map((c) => [Number(c.offering_id), c])))
const catalogDescription = computed(() => role.value === 'STUDENT'
  ? 'Browse open classes, manage active registrations, and withdraw from unused courses.'
  : 'Browse classes, sections, availability and semester information.')

const filtered = computed(() => {
  const q = query.value.toLowerCase().trim()
  if (!q) return offerings.value
  return offerings.value.filter((o) => `${o.course_code} ${o.course_name} ${o.semester_name} ${o.academic_year} ${o.section_code} ${o.offering_status}`.toLowerCase().includes(q))
})
function existing(o) { return enrollmentByOffering.value.get(Number(o.offering_id)) }
function canEnroll(o) { return role.value === 'STUDENT' && o.offering_status === 'OPEN' && !existing(o) }
function canDrop(o) { return role.value === 'STUDENT' && o.offering_status === 'OPEN' && existing(o)?.enrollment_status === 'ENROLLED' }
function canOpenWorkspace(o) { return ['ENROLLED', 'COMPLETED'].includes(existing(o)?.enrollment_status) }

async function load() {
  loading.value = true; error.value = ''
  try {
    const tasks = [api.academics.offerings(1, 200)]
    if (role.value === 'STUDENT') tasks.push(api.academics.studentDashboard())
    const [o, dashboard] = await Promise.all(tasks)
    offerings.value = o?.results || o?.items || o || []
    studentCourses.value = dashboard?.courses || []
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
function askEnroll(o) { selectedOffering.value = o }
async function confirmEnroll() {
  const o = selectedOffering.value
  if (!o) return
  selectedOffering.value = null
  enrollingId.value = o.offering_id
  try { await api.academics.enroll(o.offering_id); toast.success(`Enrolled in ${o.course_code}.`); await load() }
  catch (e) { toast.error(e.message) }
  finally { enrollingId.value = null }
}

function askDrop(o) { selectedDropOffering.value = o }
async function confirmDrop() {
  const o = selectedDropOffering.value
  if (!o) return
  selectedDropOffering.value = null
  droppingId.value = o.offering_id
  try {
    await api.academics.dropCourse(o.offering_id)
    toast.success(`Dropped ${o.course_code}.`)
    await load()
  } catch (e) { toast.error(e.message) }
  finally { droppingId.value = null }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <template #title>Course Catalog</template>
    <div class="page-heading"><div><div class="eyebrow">Academic catalog</div><h1>Courses & classes</h1><p>{{ catalogDescription }}</p></div></div>
    <div v-if="error" class="notice notice-error">{{ error }}</div>
    <LoadingState v-else-if="loading" message="Loading course catalog…" />
    <SectionCard v-else title="Available classes" :subtitle="`${offerings.length} class(es) loaded`">
      <template #actions><input v-model="query" class="input" style="width:280px" placeholder="Search course, semester or status" /></template>
      <div class="grid grid-3">
        <article v-for="o in filtered" :key="o.offering_id" class="course-card">
          <div class="course-code">{{ o.course_code }}</div><h3>{{ o.course_name }}</h3>
          <div class="course-meta">{{ o.semester_name }} · {{ o.academic_year }}<br />Section {{ o.section_code }} · Capacity {{ o.capacity }}</div>
          <div class="badge-row" style="margin-top:9px"><StatusBadge :value="o.offering_status" /><StatusBadge v-if="existing(o)" :value="existing(o).enrollment_status" /></div>
          <div class="course-card-actions">
            <RouterLink class="btn btn-secondary btn-sm" :to="`/offerings/${o.offering_id}`">{{ canOpenWorkspace(o) ? 'Open workspace' : 'View' }}</RouterLink>
            <button v-if="canEnroll(o)" class="btn btn-primary btn-sm" :disabled="enrollingId===o.offering_id" @click="askEnroll(o)">{{ enrollingId===o.offering_id ? 'Enrolling…' : 'Enroll' }}</button>
            <button v-if="canDrop(o)" class="btn btn-danger btn-sm" :disabled="droppingId===o.offering_id || enrollingId===o.offering_id" @click="askDrop(o)">{{ droppingId===o.offering_id ? 'Dropping…' : 'Drop Course' }}</button>
            <span v-else-if="role==='STUDENT' && existing(o)" class="inline-state">{{ existing(o).enrollment_status === 'DROPPED' ? 'Withdrawn' : 'Already registered' }}</span>
          </div>
        </article>
      </div>
    </SectionCard>
    <ConfirmDialog :open="!!selectedDropOffering" title="Drop this course?" :message="`Withdraw from ${selectedDropOffering?.course_code || 'this class'}? This is only allowed before attendance, quiz attempts, submissions, or grades exist. The enrollment record will be kept as DROPPED.`" confirm-label="Drop Course" tone="danger" :busy="droppingId!==null" @cancel="selectedDropOffering=null" @confirm="confirmDrop" />
    <ConfirmDialog :open="!!selectedOffering" title="Confirm enrollment" :message="`Enroll in ${selectedOffering?.course_code || 'this class'} — Section ${selectedOffering?.section_code || ''}?`" confirm-label="Enroll" @cancel="selectedOffering=null" @confirm="confirmEnroll" />
  </AppShell>
</template>
