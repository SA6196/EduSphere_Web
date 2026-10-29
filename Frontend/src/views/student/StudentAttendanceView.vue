<script setup>
import { computed, onMounted, ref } from 'vue'
import AppShell from '../../components/AppShell.vue'
import SectionCard from '../../components/SectionCard.vue'
import LoadingState from '../../components/LoadingState.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import AttendanceAnalytics from '../../components/AttendanceAnalytics.vue'
import { api } from '../../services/api.js'

const report = ref({ semesters: [], courses: [], sessions: [] })
const selectedSemesterId = ref('')
const search = ref('')
const loading = ref(true)
const error = ref('')

const semesterOptions = computed(() =>
  [...(report.value.semesters || [])]
    .sort((a, b) => String(b.semester_start_date || '').localeCompare(String(a.semester_start_date || '')) || Number(b.semester_id) - Number(a.semester_id))
    .map(s => ({ value: String(s.semester_id), label: `${s.semester_name} ${s.academic_year}` }))
)
const selectedSemesterLabel = computed(() =>
  semesterOptions.value.find(s => s.value === selectedSemesterId.value)?.label || ''
)
const semesterCourses = computed(() => {
  const query = search.value.trim().toLowerCase()
  return (report.value.courses || []).filter(course =>
    selectedSemesterId.value && String(course.semester_id) === selectedSemesterId.value &&
    (!query || [course.course_code, course.course_name, course.section_code]
      .some(value => String(value ?? '').toLowerCase().includes(query)))
  )
})
const semesterSessions = computed(() =>
  (report.value.sessions || []).filter(s =>
    selectedSemesterId.value && String(s.semester_id) === selectedSemesterId.value
  )
)
const sessionsByOffering = computed(() => {
  const grouped = new Map()
  for (const session of semesterSessions.value) {
    const id = String(session.offering_id)
    if (!grouped.has(id)) grouped.set(id, [])
    grouped.get(id).push(session)
  }
  return grouped
})
const courseSummaries = computed(() => semesterCourses.value.map(course => {
  const sessions = sessionsByOffering.value.get(String(course.offering_id)) || []
  const count = status => sessions.filter(s => s.attendance_status === status).length
  return {
    ...course,
    sessions,
    total: sessions.length,
    recorded: sessions.filter(s => s.attendance_status != null).length,
    present: count('PRESENT'),
    absent: count('ABSENT'),
    late: count('LATE'),
    excused: count('EXCUSED'),
    unrecorded: sessions.filter(s => s.attendance_status == null && s.session_timing !== 'UPCOMING').length,
  }
}))
const semesterTotals = computed(() => courseSummaries.value.reduce((totals, course) => {
  for (const key of ['total', 'recorded', 'present', 'absent', 'late', 'excused', 'unrecorded']) totals[key] += course[key]
  return totals
}, { total: 0, recorded: 0, present: 0, absent: 0, late: 0, excused: 0, unrecorded: 0 }))
function attendanceLabel(session) {
  if (session.attendance_status) return session.attendance_status
  return session.session_timing === 'UPCOMING' ? 'Upcoming' : 'Not recorded'
}

onMounted(async () => {
  try {
    report.value = await api.attendance.mySemester() || { semesters: [], courses: [], sessions: [] }
    selectedSemesterId.value = semesterOptions.value[0]?.value || ''
  } catch (e) {
    error.value = e.message || 'Unable to load attendance.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <AppShell>
    <template #title>Attendance</template>
    <div v-if="error" class="notice notice-error" role="alert">{{ error }}</div>
    <LoadingState v-else-if="loading" message="Loading semester-wise attendance…" />
    <SectionCard v-else title="Semester-wise attendance" subtitle="Select a semester to view attendance for all your enrolled courses.">
      <div class="semester-picker">
        <label for="attendance-semester" class="semester-picker-label">Select Semester</label>
        <select id="attendance-semester" v-model="selectedSemesterId" class="select semester-picker-select">
          <option value="" disabled>-- Choose Semester --</option>
          <option v-for="semester in semesterOptions" :key="semester.value" :value="semester.value">{{ semester.label }}</option>
        </select>
      </div>
      <div v-if="!semesterOptions.length" class="notice notice-info">No enrolled semesters found.</div>
      <template v-else-if="selectedSemesterId">
        <div class="semester-summary" aria-live="polite">
          <strong>{{ selectedSemesterLabel }}</strong>
          <span>{{ courseSummaries.length }} course(s)</span>
          <span>{{ semesterTotals.recorded }} / {{ semesterTotals.total }} sessions marked</span>
          <span>{{ semesterTotals.present }} present</span>
          <span>{{ semesterTotals.absent }} absent</span>
          <span>{{ semesterTotals.late }} late</span>
          <span>{{ semesterTotals.excused }} excused</span>
        </div>
        <div class="attendance-search">
          <label for="attendance-course-search">Search courses</label>
          <input id="attendance-course-search" v-model="search" class="input" type="search" placeholder="Course code, name or section…" />
        </div>
        <AttendanceAnalytics :courses="semesterCourses" :sessions="semesterSessions" />
        <div v-if="!courseSummaries.length" class="notice notice-info">No courses match this semester and search.</div>
        <section v-for="course in courseSummaries" :key="course.offering_id" class="attendance-course">
          <div class="attendance-course-head">
            <div>
              <h3>{{ course.course_code }} · {{ course.course_name }}</h3>
              <p>Section {{ course.section_code || '—' }} · {{ course.enrollment_status }}</p>
            </div>
            <strong>{{ course.recorded }} / {{ course.total }} sessions marked</strong>
          </div>
          <div class="attendance-summary">
            <span><strong>{{ course.present }}</strong> Present</span>
            <span><strong>{{ course.absent }}</strong> Absent</span>
            <span><strong>{{ course.late }}</strong> Late</span>
            <span><strong>{{ course.excused }}</strong> Excused</span>
            <span><strong>{{ course.unrecorded }}</strong> Not recorded</span>
          </div>
          <div v-if="!course.sessions.length" class="notice notice-info attendance-empty">No class sessions have been scheduled for this course.</div>
          <div v-else class="table-wrap">
            <table class="data-table" :aria-label="`Attendance history for ${course.course_code}`">
              <thead><tr><th scope="col">Date</th><th scope="col">Time</th><th scope="col">Session</th><th scope="col">Topic</th><th scope="col">Attendance</th><th scope="col">Remarks</th></tr></thead>
              <tbody>
                <tr v-for="session in course.sessions" :key="session.session_id">
                  <td>{{ session.session_date }}</td>
                  <td>{{ session.start_time || '—' }}<span v-if="session.end_time"> – {{ session.end_time }}</span></td>
                  <td>{{ session.session_type || '—' }}</td>
                  <td>{{ session.topic || '—' }}</td>
                  <td><StatusBadge v-if="session.attendance_status" :value="session.attendance_status" /><span v-else class="pending-attendance">{{ attendanceLabel(session) }}</span></td>
                  <td>{{ session.remarks || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <p class="attendance-note">Attendance reflects instructor-recorded entries only. A session without a record is marked “Not recorded,” not “Absent.” Future sessions are marked “Upcoming.” Late and excused attendance are reported separately because institutional percentage rules may differ.</p>
      </template>
    </SectionCard>
  </AppShell>
</template>

<style scoped>
.semester-picker { display: grid; grid-template-columns: 190px minmax(220px, 520px); align-items: center; justify-content: center; gap: 20px; padding: 24px 20px; margin-bottom: 18px; background: var(--surface-subtle, #f8fafc); border: 1px solid var(--border, #e2e8f0); border-radius: 12px; }
.semester-picker-label { font-weight: 700; font-size: 14px; }
.semester-picker-select { width: 100%; }
.semester-summary { display: flex; gap: 10px 18px; flex-wrap: wrap; align-items: center; padding: 12px 16px; margin-bottom: 16px; border-radius: 10px; background: var(--surface-subtle, #f8fafc); color: var(--text-muted, #64748b); font-size: 13px; }
.semester-summary strong { color: var(--text-primary, #0f172a); font-size: 15px; margin-right: auto; }
.attendance-search { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 0 0 16px; font-size: 13px; font-weight: 650; }
.attendance-search .input { width: min(100%, 360px); }
.attendance-course { border: 1px solid var(--border, #e2e8f0); border-radius: 12px; overflow: hidden; margin: 20px 0; }
.attendance-course-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; padding: 16px 18px; background: var(--surface-subtle, #f8fafc); }
.attendance-course-head h3 { font-size: 16px; margin: 0; }
.attendance-course-head p { font-size: 12px; margin: 5px 0 0; color: var(--text-muted, #64748b); }
.attendance-course-head > strong { font-size: 13px; }
.attendance-summary { display: flex; flex-wrap: wrap; gap: 10px 20px; padding: 12px 18px; border-bottom: 1px solid var(--border, #e2e8f0); font-size: 13px; }
.attendance-summary span strong { margin-right: 4px; }
.attendance-course .data-table { width: 100%; min-width: 700px; }
.attendance-course .table-wrap { overflow-x: auto; }
.attendance-empty { margin: 12px; }
.pending-attendance { color: var(--text-muted, #64748b); }
.attendance-note { font-size: 12px; color: var(--text-muted, #64748b); }
@media (max-width: 700px) { .semester-picker { grid-template-columns: 1fr; gap: 8px; } .semester-summary strong { width: 100%; } .attendance-course-head { align-items: flex-start; } }
</style>
