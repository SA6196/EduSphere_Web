<script setup>
import { computed, onMounted, ref } from 'vue'
import AppShell from '../../components/AppShell.vue'
import StatCard from '../../components/StatCard.vue'
import SectionCard from '../../components/SectionCard.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import EmptyState from '../../components/EmptyState.vue'
import DataTable from '../../components/DataTable.vue'
import { api } from '../../services/api.js'
import { compactNumber, percent } from '../../utils/format.js'

const dashboard = ref(null)
const exams = ref([])
const gpa = ref(null)
const error = ref('')
const loading = ref(true)

const activeCourses = computed(() => dashboard.value?.courses?.filter((c) => c.enrollment_status === 'ENROLLED') || [])
const avgAttendance = computed(() => {
  const vals = (dashboard.value?.courses || []).map((c) => Number(c.attendance_percentage)).filter(Number.isFinite)
  return vals.length ? vals.reduce((a,b) => a+b,0) / vals.length : null
})

onMounted(async () => {
  try {
    const [d, e, g] = await Promise.all([api.academics.studentDashboard(), api.exams.upcoming(), api.gpa.my()])
    dashboard.value = d
    exams.value = e || []
    gpa.value = g
  } catch (e) { error.value = e.message } finally { loading.value = false }
})
</script>

<template>
  <AppShell>
    <template #title>Student Dashboard</template>
    <div class="page-heading">
      <div><div class="eyebrow">Student portal</div><h1>{{ dashboard?.profile?.student_name || 'Your learning dashboard' }}</h1><p>Track courses, attendance, assessment progress and upcoming exams.</p></div>
      <RouterLink class="btn btn-primary" to="/catalog">Browse courses</RouterLink>
    </div>

    <div v-if="error" class="notice notice-error">{{ error }}</div>
    <template v-else-if="!loading && dashboard">
      <div class="stats-grid">
        <StatCard label="CGPA" :value="compactNumber(dashboard.profile.cgpa ?? gpa?.cgpa)" icon="A" hint="Published course grades" />
        <StatCard label="Active courses" :value="activeCourses.length" icon="▦" hint="Currently enrolled" />
        <StatCard label="Avg. attendance" :value="percent(avgAttendance)" icon="✓" hint="Across available course records" />
        <StatCard label="Upcoming exams" :value="exams.length" icon="◷" hint="Scheduled future exams" />
      </div>

      <SectionCard title="Quick access" subtitle="Jump straight to the areas students use most.">
        <div class="quick-access-grid">
          <RouterLink class="quick-access-card" to="/student/quiz-attempts"><span class="quick-access-icon">✓</span><span><strong>Quiz attempts</strong><small>Review submitted quizzes and released marks.</small></span><span class="quick-access-arrow">→</span></RouterLink>
          <RouterLink class="quick-access-card" to="/student/performance"><span class="quick-access-icon">↗</span><span><strong>My performance</strong><small>Check semester-wise marks, GPA and exams.</small></span><span class="quick-access-arrow">→</span></RouterLink>
          <RouterLink class="quick-access-card" to="/student/attendance"><span class="quick-access-icon">▤</span><span><strong>My attendance</strong><small>View course attendance by semester.</small></span><span class="quick-access-arrow">→</span></RouterLink>
          <RouterLink class="quick-access-card" to="/catalog"><span class="quick-access-icon">▦</span><span><strong>Course catalog</strong><small>Explore available classes and offerings.</small></span><span class="quick-access-arrow">→</span></RouterLink>
        </div>
      </SectionCard>

      <SectionCard title="Upcoming exams" subtitle="Keep your next scheduled assessments in view.">
        <DataTable v-if="exams.length" :rows="exams" :columns="[{key:'course_code',label:'Course'},{key:'exam_title',label:'Exam'},{key:'exam_type',label:'Type'},{key:'exam_date',label:'Date'},{key:'start_time',label:'Start'},{key:'end_time',label:'End'}]" empty="No upcoming exams scheduled." />
        <EmptyState v-else title="No upcoming exams" message="There are no upcoming exams scheduled for your enrolled courses." />
        <div class="section-footer-action"><RouterLink class="btn btn-secondary btn-sm" to="/student/performance">View full performance overview</RouterLink></div>
      </SectionCard>

      <SectionCard title="My courses" subtitle="Open a class workspace for learning materials, assessments and course activity.">
        <div v-if="dashboard.courses?.length" class="grid grid-3">
          <article v-for="course in dashboard.courses" :key="course.enrollment_id" class="course-card">
            <div class="course-code">{{ course.course_code }}</div>
            <h3>{{ course.course_name }}</h3>
            <div class="course-meta">{{ course.semester_name }} · {{ course.academic_year }} · Section {{ course.section_code }}</div>
            <div style="display:flex;gap:7px;margin-top:9px"><StatusBadge :value="course.enrollment_status" /><StatusBadge :value="course.offering_status" /></div>
            <div class="course-card-actions"><RouterLink class="btn btn-secondary btn-sm" :to="`/offerings/${course.offering_id}`">Open workspace</RouterLink></div>
          </article>
        </div>
        <EmptyState v-else title="No courses yet" message="Browse the catalog to view available classes." />
      </SectionCard>
    </template>
  </AppShell>
</template>
