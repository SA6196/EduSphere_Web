<script setup>
import { onMounted, ref } from 'vue'
import AppShell from '../../components/AppShell.vue'
import StatCard from '../../components/StatCard.vue'
import SectionCard from '../../components/SectionCard.vue'
import DataTable from '../../components/DataTable.vue'
import LoadingState from '../../components/LoadingState.vue'
import { api } from '../../services/api.js'

const summary = ref(null)
const overview = ref(null)
const semesters = ref([])
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const [s, o, sem] = await Promise.all([api.academics.adminSummary(), api.reports.overview(), api.reports.semesters()])
    summary.value = s; overview.value = o; semesters.value = sem || []
  } catch (e) { error.value = e.message } finally { loading.value = false }
})
</script>

<template>
  <AppShell>
    <template #title>Administrator Dashboard</template>
    <div class="page-heading"><div><div class="eyebrow">Administration</div><h1>LMS operational overview</h1><p>Monitor users, classes, enrollments and academic activity across EduSphere.</p></div><div class="page-actions"><RouterLink class="btn btn-soft" to="/admin/management">Academic management</RouterLink><RouterLink class="btn btn-primary" to="/admin/reports">Open reports</RouterLink></div></div>
    <div v-if="error" class="notice notice-error">{{ error }}</div>
    <LoadingState v-else-if="loading" message="Loading administrative overview…" />
    <template v-else-if="overview">
      <div class="stats-grid">
        <StatCard label="Students" :value="overview.total_students" icon="S" />
        <StatCard label="Instructors" :value="overview.total_instructors" icon="I" />
        <StatCard label="Classes" :value="overview.total_classes" icon="▦" :hint="`${overview.open_classes || 0} open`" />
        <StatCard label="Active enrollments" :value="overview.active_enrollments" icon="↗" />
      </div>
      <div class="grid grid-2">
        <SectionCard title="Academic content">
          <div class="grid grid-3">
            <StatCard label="Assignments" :value="overview.total_assignments" icon="✎" />
            <StatCard label="Quizzes" :value="overview.total_quizzes" icon="?" />
            <StatCard label="Exams" :value="overview.total_exams" icon="◷" />
          </div>
        </SectionCard>
        <SectionCard title="Published & communication">
          <div class="grid grid-3">
            <StatCard label="Grades" :value="overview.published_grades" icon="A" />
            <StatCard label="Announcements" :value="overview.total_announcements" icon="!" />
            <StatCard label="Materials" :value="overview.total_materials" icon="□" />
          </div>
        </SectionCard>
      </div>
      <SectionCard title="Semesters"><DataTable :rows="semesters" :columns="[{key:'semester_name',label:'Semester'},{key:'academic_year',label:'Academic year'},{key:'semester_start_date',label:'Start date'},{key:'semester_end_date',label:'End date'}]" /></SectionCard>
    </template>
  </AppShell>
</template>
