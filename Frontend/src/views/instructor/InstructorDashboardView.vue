<script setup>
import { computed, onMounted, ref } from 'vue'
import AppShell from '../../components/AppShell.vue'
import StatCard from '../../components/StatCard.vue'
import SectionCard from '../../components/SectionCard.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import EmptyState from '../../components/EmptyState.vue'
import { api } from '../../services/api.js'

const offerings = ref([])
const questionCount = ref(0)
const error = ref('')
const loading = ref(true)

const openCount = computed(() => offerings.value.filter(o => o.offering_status === 'OPEN').length)
const plannedCount = computed(() => offerings.value.filter(o => o.offering_status === 'PLANNED').length)

async function load() {
  loading.value = true
  error.value = ''
  const [offeringsResult, questionsResult] = await Promise.allSettled([
    api.academics.instructorOfferings(),
    api.quizzes.questions(),
  ])

  if (offeringsResult.status === 'fulfilled') {
    offerings.value = Array.isArray(offeringsResult.value) ? offeringsResult.value : []
  } else {
    error.value = offeringsResult.reason?.message || 'Unable to load assigned classes.'
  }

  if (questionsResult.status === 'fulfilled') {
    const value = questionsResult.value
    questionCount.value = Array.isArray(value) ? value.length : Number(value?.count ?? value?.results?.length ?? value?.items?.length ?? 0)
  }

  loading.value = false
}

onMounted(load)
</script>

<template>
  <AppShell>
    <template #title>Instructor Dashboard</template>
    <div class="page-heading"><div><div class="eyebrow">Instructor portal</div><h1>Teaching workspace</h1><p>Manage assigned classes, course content, attendance, assessments and grading.</p></div><RouterLink class="btn btn-primary" to="/question-bank">Question bank</RouterLink></div>
    <div v-if="error" class="notice notice-error">{{ error }}</div>
    <LoadingState v-else-if="loading" message="Loading teaching workspace…" />
    <template v-else>
      <div class="stats-grid">
        <StatCard label="Assigned classes" :value="offerings.length" icon="▦" />
        <StatCard label="Open classes" :value="openCount" icon="○" />
        <StatCard label="Planned classes" :value="plannedCount" icon="◷" />
        <StatCard label="Question bank" :value="questionCount" icon="?" hint="Reusable questions" />
      </div>
      <SectionCard title="My classes" subtitle="Open a class to manage roster, grading, materials, announcements, sessions, assignments, quizzes and exams.">
        <div v-if="offerings.length" class="grid grid-3">
          <article v-for="offering in offerings" :key="offering.offering_id" class="course-card">
            <div class="course-code">{{ offering.course_code }}</div><h3>{{ offering.course_name }}</h3>
            <div class="course-meta">Section {{ offering.section_code }} · Capacity {{ offering.capacity }}</div>
            <div style="margin-top:9px"><StatusBadge :value="offering.offering_status" /></div>
            <div class="course-card-actions"><RouterLink class="btn btn-primary btn-sm" :to="`/offerings/${offering.offering_id}`">Manage class</RouterLink></div>
          </article>
        </div>
        <EmptyState v-else title="No assigned classes" message="There are no classes assigned to this instructor account." />
      </SectionCard>
    </template>
  </AppShell>
</template>
