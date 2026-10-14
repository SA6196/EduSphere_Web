<script setup>
import { computed, onMounted, ref } from 'vue'
import AppShell from '../../components/AppShell.vue'
import SectionCard from '../../components/SectionCard.vue'
import DataTable from '../../components/DataTable.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import LoadingState from '../../components/LoadingState.vue'
import BarChart from '../../components/BarChart.vue'
import CalendarMonth from '../../components/CalendarMonth.vue'
import { api } from '../../services/api.js'
import { compactNumber } from '../../utils/format.js'

const marks = ref([])
const semesterMarkbook = ref({ semesters: [], components: [] })
const selectedSemesterId = ref('')
const assessmentSearch = ref('')

// Semesters come from the student's own course enrollments, not just posted
// marks. Show one VTOP-style selector ordered from newest to oldest.
const semesterOptions = computed(() =>
  [...(semesterMarkbook.value.semesters || [])]
    .sort((a, b) => String(b.semester_start_date || '').localeCompare(String(a.semester_start_date || '')) || Number(b.semester_id) - Number(a.semester_id))
    .map(s => ({
      value: String(s.semester_id),
      label: `${s.semester_name} ${s.academic_year}`,
    }))
)
const selectedSemesterLabel = computed(() =>
  semesterOptions.value.find(s => s.value === selectedSemesterId.value)?.label || ''
)
const selectedSemesterComponents = computed(() =>
  (semesterMarkbook.value.components || []).filter(row =>
    selectedSemesterId.value && String(row.semester_id) === selectedSemesterId.value
  )
)
const filteredMarks = computed(() => marks.value.filter(m =>
  selectedSemesterId.value && String(m.semester_id) === selectedSemesterId.value
))
const visibleSemesterComponents = computed(() => {
  const query = assessmentSearch.value.trim().toLocaleLowerCase()
  if (!query) return selectedSemesterComponents.value
  return selectedSemesterComponents.value.filter(row =>
    [row.course_code, row.course_name, row.component_name, row.component_type,
      row.exam_title, row.exam_type, row.section_code].some(v =>
      String(v ?? '').toLocaleLowerCase().includes(query)
    )
  )
})
const courseMarkbook = computed(() => {
  const groups = new Map()
  for (const component of visibleSemesterComponents.value) {
    const key = String(component.offering_id)
    if (!groups.has(key)) {
      groups.set(key, {
        offering_id: component.offering_id,
        course_code: component.course_code,
        course_name: component.course_name,
        section_code: component.section_code,
        components: [],
      })
    }
    groups.get(key).components.push(component)
  }
  return [...groups.values()].sort((a, b) =>
    String(a.course_code).localeCompare(String(b.course_code)) ||
    String(a.section_code || '').localeCompare(String(b.section_code || ''))
  )
})
const semesterRecordedCount = computed(() =>
  selectedSemesterComponents.value.filter(row => row.mark_status === 'RECORDED').length
)
const semesterPastExamDates = computed(() =>
  selectedSemesterComponents.value.filter(row => row.exam_status === 'PAST_DATE').length
)
function showMarks(row) {
  if (row.mark_status === 'HIDDEN') return 'Not released'
  if (row.mark_status !== 'RECORDED') return 'Awaiting marks'
  return `${row.marks_obtained} / ${row.max_marks}`
}
function examDescription(row) {
  if (!row.exam_id) return row.component_type === 'EXAM' ? 'Not scheduled' : '—'
  const status = row.exam_status === 'PAST_DATE' ? 'Date passed' :
    row.exam_status === 'TODAY' ? 'Today' : 'Scheduled'
  return `${status} · ${row.exam_date || 'Date not set'}`
}
function gradeState(row) {
  if (row.mark_status === 'HIDDEN') return 'Not released'
  if (row.mark_status === 'RECORDED') return 'Recorded'
  return 'Pending'
}
// A graded quiz has its own total. This is not always equal to the
// component maximum configured by an instructor. Surface discrepancies.
const quizMaxWarnings = computed(() => {
  const warnings = []
  for (const mark of filteredMarks.value) {
    if (String(mark.component_type || '').toUpperCase() !== 'QUIZ') continue
    const attempts = quizAttempts.value.filter(a =>
      a.marks_visible && String(a.component_id) === String(mark.component_id) &&
      Number.isFinite(Number(a.marks_obtained)) && Number.isFinite(Number(a.max_marks))
    )
    if (!attempts.length) continue
    attempts.sort((a, b) => Number(b.marks_obtained) - Number(a.marks_obtained) || Number(b.attempt_no) - Number(a.attempt_no))
    const best = attempts[0]
    if (Math.abs(Number(mark.max_marks) - Number(best.max_marks)) > 0.001) {
      warnings.push(`${mark.component_name}: assessment maximum ${mark.max_marks} differs from the best attempt's quiz maximum ${best.max_marks}. The instructor should check the quiz question totals and assessment configuration.`)
    }
  }
  return warnings
})
const gpa = ref(null)
const exams = ref([])
const quizAttempts = ref([])
const error = ref('')
const loading = ref(true)

const gpaSemesters = computed(() => gpa.value?.semesters || [])
const gpaChart = computed(() => gpaSemesters.value.map((s) => ({ key:s.semester_id, label:`${s.semester_name} ${s.academic_year}`, value:Number(s.sgpa), hint:`${s.graded_course_count} graded course(s)` })))
const examEvents = computed(() => exams.value.map((e) => ({ key:e.exam_id, date:e.exam_date, label:`${e.start_time || ''} ${e.course_code || ''}`.trim(), detail:`${e.course_code || ''} · ${e.exam_title || 'Exam'} · ${e.exam_type || ''} · ${e.start_time || '—'}${e.end_time?`–${e.end_time}`:''}` })))

onMounted(async () => {
  loading.value = true
  try {
    const [m,g,e,q,markbook] = await Promise.all([
      api.academics.myMarks(), api.gpa.my(),
      api.exams.upcoming(), api.quizzes.attempts(), api.academics.mySemesterMarkbook(),
    ])
    marks.value = m || []; gpa.value = g;
    exams.value = e || []; quizAttempts.value = q?.attempts || []
    semesterMarkbook.value = markbook || { semesters: [], components: [] }
    selectedSemesterId.value = semesterOptions.value[0]?.value || '' 
  } catch (e) { error.value = e.message } finally { loading.value = false }
})
</script>

<template>
  <AppShell>
    <template #title>Performance</template>
    <div v-if="error" class="notice notice-error">{{error}}</div>
    <LoadingState v-else-if="loading" message="Loading academic performance…" />
    <template v-else>
      <SectionCard title="Semester-wise marks view" subtitle="Select a semester to see every assessment component, exam dates, and recorded marks for each course.">
        <div class="semester-picker">
          <label for="marks-semester" class="semester-picker-label">Select Semester</label>
          <select id="marks-semester" v-model="selectedSemesterId" class="select semester-picker-select">
            <option value="" disabled>-- Choose Semester --</option>
            <option v-for="semester in semesterOptions" :key="semester.value" :value="semester.value">{{ semester.label }}</option>
          </select>
        </div>
        <div v-if="!semesterOptions.length" class="notice notice-info" role="status">No semesters are available for your enrollments.</div>
        <template v-else-if="selectedSemesterId">
          <div class="semester-summary" aria-live="polite">
            <strong>{{ selectedSemesterLabel }}</strong>
            <span>{{ courseMarkbook.length }} course(s)</span>
            <span>{{ selectedSemesterComponents.length }} assessment component(s)</span>
            <span>{{ semesterRecordedCount }} marks recorded</span>
            <span>{{ semesterPastExamDates }} past exam dates</span>
          </div>
          <div class="markbook-search-row">
            <label for="markbook-search">Search courses or assessments</label>
            <input id="markbook-search" v-model="assessmentSearch" class="input markbook-search" placeholder="Search course code, exam or component…" type="search" />
          </div>
          <p v-for="warning in quizMaxWarnings" :key="warning" class="notice notice-info" role="status">{{ warning }}</p>
          <div v-if="!courseMarkbook.length" class="notice notice-info">{{ assessmentSearch ? 'No courses or assessments match this search.' : 'No assessment components are configured for this semester yet.' }}</div>
          <section v-for="course in courseMarkbook" :key="course.offering_id" class="course-markbook">
            <div class="course-markbook-head">
              <div>
                <h3>{{ course.course_code }} · {{ course.course_name }}</h3>
                <p v-if="course.section_code">Section {{ course.section_code }}</p>
              </div>
              <span class="course-markbook-count">{{ course.components.length }} component(s)</span>
            </div>
            <div class="table-wrap">
              <table class="data-table" :aria-label="`Assessment marks for ${course.course_code}`">
                <thead><tr>
                  <th scope="col">Assessment component / exam</th>
                  <th scope="col">Type</th>
                  <th scope="col">Exam date / status</th>
                  <th scope="col">Component maximum</th>
                  <th scope="col">Marks obtained</th>
                  <th scope="col">Status</th>
                </tr></thead>
                <tbody>
                  <tr v-for="component in course.components" :key="`${component.enrollment_id}:${component.component_id}`">
                    <td>
                      <strong>{{ component.component_name }}</strong>
                      <div v-if="component.exam_title && component.exam_title !== component.component_name" class="course-meta">{{ component.exam_title }}</div>
                      <div v-if="component.recorded_at && component.mark_status === 'RECORDED'" class="course-meta">Recorded {{ new Date(component.recorded_at).toLocaleDateString() }}</div>
                    </td>
                    <td>{{ component.exam_type || component.component_type }}</td>
                    <td>{{ examDescription(component) }}</td>
                    <td>{{ component.max_marks }}</td>
                    <td><strong :class="{ 'mark-muted': component.mark_status !== 'RECORDED' }">{{ showMarks(component) }}</strong></td>
                    <td><span class="mark-state" :class="{ 'mark-state-recorded': component.mark_status === 'RECORDED' }">{{ gradeState(component) }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
          <p class="course-markbook-footnote">Quiz attempt totals may differ from the assessment component maximum. Scores are displayed as stored; the system does not automatically rescale past marks. The exam date comes from its schedule: a past date does not confirm that the exam actually took place. Exams without recorded marks are shown as pending, not zero.</p>
        </template>
      </SectionCard>
      <SectionCard title="My quiz attempts" subtitle="Recent attempts are shown below. Older submitted attempts remain available in your full attempt history.">
        <div v-if="quizAttempts.length > 8" class="marks-attempt-history-note">
          Showing 8 most recent attempts of {{ quizAttempts.length }}.
          <RouterLink to="/student/quiz-attempts">View all attempts</RouterLink>
        </div>
        <div v-if="quizAttempts.length" class="table-wrap">
          <table class="data-table"><thead><tr><th>Quiz</th><th>Attempt</th><th>Submitted</th><th>Marks</th><th></th></tr></thead><tbody>
            <tr v-for="attempt in quizAttempts.slice(0, 8)" :key="attempt.attempt_id">
              <td><strong>{{ attempt.quiz_title }}</strong><div class="course-meta">{{ attempt.course_code }} · {{ attempt.course_name }}</div></td>
              <td>#{{ attempt.attempt_no }}</td>
              <td>{{ attempt.submitted_at ? new Date(attempt.submitted_at).toLocaleString() : '—' }}</td>
              <td>{{ attempt.marks_visible ? `${attempt.marks_obtained} / ${attempt.max_marks}` : (attempt.grading_status ? 'Hidden' : 'Awaiting grading') }}</td>
              <td><RouterLink class="btn btn-soft btn-sm" to="/student/quiz-attempts">View attempt</RouterLink></td>
            </tr>
          </tbody></table>
        </div>
        <div v-else class="notice notice-info">No submitted quiz attempts yet.</div>
      </SectionCard>

      <div class="grid grid-2">
        <SectionCard title="Semester GPA trend" subtitle="SGPA values calculated from published grades."><BarChart :items="gpaChart" :max="10" /></SectionCard>
        <SectionCard title="GPA verification">
          <div class="metric-list">
            <div class="metric-pair"><span>CGPA</span><strong>{{compactNumber(gpa?.cgpa)}}</strong></div>
            <div class="metric-pair"><span>Verified CGPA</span><strong>{{compactNumber(gpa?.verified_cgpa)}}</strong></div>
            <div class="metric-pair"><span>Verification</span><StatusBadge :value="gpa?.cgpa_verification" /></div>
            <div class="metric-pair"><span>Graded credits</span><strong>{{gpa?.total_graded_credits ?? '—'}}</strong></div>
          </div>
        </SectionCard>
      </div>
      <SectionCard title="Semester GPA details"><DataTable :rows="gpaSemesters" :columns="[{key:'semester_name',label:'Semester'},{key:'academic_year',label:'Academic year'},{key:'sgpa',label:'SGPA'},{key:'graded_course_count',label:'Courses'},{key:'graded_credits',label:'Credits'},{key:'verification',label:'Verification'}]"><template #cell-verification="{value}"><StatusBadge :value="value" /></template></DataTable></SectionCard>

      <div class="grid grid-2 calendar-table-grid"><CalendarMonth :events="examEvents" title="Upcoming exam calendar" /><SectionCard title="Upcoming exams"><DataTable :rows="exams" :columns="[{key:'course_code',label:'Course'},{key:'exam_title',label:'Exam'},{key:'exam_type',label:'Type'},{key:'exam_date',label:'Date'},{key:'start_time',label:'Start'},{key:'end_time',label:'End'}]" /></SectionCard></div>
    </template>
  </AppShell>
</template>

<style scoped>
.semester-picker { display: grid; grid-template-columns: 190px minmax(220px, 520px); align-items: center; justify-content: center; gap: 20px; padding: 24px 20px; margin-bottom: 18px; background: var(--surface-subtle, #f8fafc); border: 1px solid var(--border, #e2e8f0); border-radius: 12px; }
.markbook-search-row { display: flex; align-items: center; flex-wrap: wrap; gap: 10px 16px; margin-bottom: 14px; }
.markbook-search-row label { font-size: 13px; font-weight: 650; }
.markbook-search { width: min(100%, 360px); }
.semester-picker-label { font-weight: 700; font-size: 14px; }
.semester-picker-select { width: 100%; }
.semester-summary { display: flex; gap: 8px 18px; flex-wrap: wrap; align-items: center; padding: 12px 16px; margin-bottom: 18px; border-radius: 10px; background: var(--surface-subtle, #f8fafc); color: var(--text-muted, #64748b); font-size: 13px; }
.semester-summary strong { font-size: 15px; color: var(--text-primary, #0f172a); margin-right: auto; }
.course-markbook { margin: 22px 0; border: 1px solid var(--border, #e2e8f0); border-radius: 12px; overflow: hidden; }
.course-markbook-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 16px 18px; background: var(--surface-subtle, #f8fafc); }
.course-markbook-head h3 { margin: 0; font-size: 16px; }
.course-markbook-head p { margin: 4px 0 0; color: var(--text-muted, #64748b); font-size: 12px; }
.course-markbook-count { font-size: 12px; color: var(--text-muted, #64748b); white-space: nowrap; }
.course-markbook .table-wrap { overflow-x: auto; }
.course-markbook .data-table { width: 100%; min-width: 730px; }
.course-markbook .data-table th, .course-markbook .data-table td { padding: 12px 14px; }
.mark-state { display: inline-block; border-radius: 6px; padding: 4px 8px; background: #f1f5f9; color: #475569; font-size: 12px; font-weight: 650; }
.mark-state-recorded { background: #eaf7ed; color: #216e35; }
.mark-muted, .course-markbook-footnote { color: var(--text-muted, #64748b); }
.course-markbook-footnote { font-size: 12px; margin-top: 16px; }
.marks-attempt-history-note { padding: 0 0 14px; font-size: 13px; color: var(--text-muted, #64748b); }
@media (max-width: 700px) { .semester-picker { grid-template-columns: 1fr; gap: 8px; } .semester-summary strong { width: 100%; } .course-markbook-head { align-items: flex-start; flex-direction: column; gap: 6px; } }
</style>
