<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppShell from '../../components/AppShell.vue'
import SectionCard from '../../components/SectionCard.vue'
import DataTable from '../../components/DataTable.vue'
import StatCard from '../../components/StatCard.vue'
import LoadingState from '../../components/LoadingState.vue'
import BarChart from '../../components/BarChart.vue'
import CalendarMonth from '../../components/CalendarMonth.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import { api } from '../../services/api.js'
import { displayLabel } from '../../utils/format.js'
import { toast } from '../../stores/toast.js'

const overview = ref(null)
const semesters = ref([])
const offerings = ref([])
const students = ref([])
const roster = ref(null)
const progress = ref(null)
const studentExams = ref(null)
const studentGpa = ref(null)
const loading = ref(true)
const pending = reactive({ roster:false, student:false })
const form = reactive({ offering_id:'', student_id:'', semester_id:'' })

function rows(data){return Array.isArray(data)?data:(data?.results||data?.items||[])}
const overviewChart = computed(() => overview.value ? [
  {label:'Students',value:overview.value.total_students}, {label:'Instructors',value:overview.value.total_instructors},
  {label:'Classes',value:overview.value.total_offerings}, {label:'Active enrollments',value:overview.value.active_enrollments},
  {label:'Published grades',value:overview.value.published_grades},
] : [])
const progressRows = computed(() => progress.value?.courses || [])
const progressChart = computed(() => progressRows.value.map(c => ({ key:c.enrollment_id, label:c.course_code, value:Number(c.course_percentage), hint:`Attendance ${c.attendance_percentage ?? '—'}%` })))
const attendanceChart = computed(() => progressRows.value.map(c => ({ key:c.enrollment_id, label:c.course_code, value:Number(c.attendance_percentage), hint:`Course ${c.course_percentage ?? '—'}%` })))
const gpaRows = computed(() => studentGpa.value?.semesters || [])
const gpaChart = computed(() => gpaRows.value.map(s => ({key:s.semester_id,label:`${s.semester_name} ${s.academic_year}`,value:Number(s.sgpa)})))
const examRows = computed(() => Array.isArray(studentExams.value) ? studentExams.value : (studentExams.value?.exams || []))
const examEvents = computed(() => examRows.value.map(e => ({key:e.exam_id,date:e.exam_date,label:`${e.start_time||''} ${e.course_code||''}`.trim(),detail:`${e.course_code||''} · ${e.exam_title||'Exam'} · ${e.exam_type||''} · ${e.start_time||'—'}${e.end_time?`–${e.end_time}`:''}`})))
const selectedStudent = computed(() => students.value.find(s=>String(s.student_id)===String(form.student_id)))

async function buildStudentDirectory(offeringRows) {
  const results = await Promise.allSettled(offeringRows.map(o => api.reports.roster(o.offering_id)))
  const map = new Map()
  for (const result of results) {
    if (result.status !== 'fulfilled') continue
    for (const s of result.value?.students || []) if (!map.has(Number(s.student_id))) map.set(Number(s.student_id), s)
  }
  students.value = [...map.values()].sort((a,b)=>String(a.student_name).localeCompare(String(b.student_name)))
}

onMounted(async () => {
  loading.value=true
  try {
    const [o, sem, offs] = await Promise.all([api.reports.overview(), api.reports.semesters(), api.academics.offerings(1,200)])
    overview.value=o; semesters.value=sem||[]; offerings.value=rows(offs)
    await buildStudentDirectory(offerings.value)
  } catch(e){toast.error(e.message)} finally{loading.value=false}
})
async function loadRoster(){pending.roster=true;try{roster.value=await api.reports.roster(Number(form.offering_id))}catch(e){toast.error(e.message)}finally{pending.roster=false}}
async function loadStudent(){pending.student=true;try{const id=Number(form.student_id), sem=Number(form.semester_id);[progress.value,studentExams.value,studentGpa.value]=await Promise.all([api.reports.progress(id,sem),api.reports.upcomingExams(id),api.gpa.student(id)])}catch(e){toast.error(e.message)}finally{pending.student=false}}
</script>

<template>
  <AppShell>
    <template #title>Administrative Reports</template>
    <div class="page-heading"><div><div class="eyebrow">Reporting</div><h1>Academic reporting center</h1><p>Select classs and students by name. Reports are rendered as structured tables, charts and calendars.</p></div></div>
    <LoadingState v-if="loading" message="Loading reporting directory…" />
    <template v-else>
      <div v-if="overview" class="stats-grid"><StatCard label="Total users" :value="overview.total_users" icon="U" /><StatCard label="Active users" :value="overview.active_users" icon="✓" /><StatCard label="Completed enrollments" :value="overview.completed_enrollments" icon="A" /><StatCard label="Published grades" :value="overview.published_grades" icon="G" /></div>
      <SectionCard title="LMS activity overview"><BarChart :items="overviewChart" /></SectionCard>

      <SectionCard title="Offering roster report">
        <form class="form-grid" @submit.prevent="loadRoster"><div class="field"><label>Class</label><select v-model="form.offering_id" class="select" required><option value="" disabled>Select class</option><option v-for="o in offerings" :key="o.offering_id" :value="o.offering_id">{{o.course_code}} · {{o.course_name}} · Section {{o.section_code}} · {{displayLabel(o.offering_status)}}</option></select></div><div class="field" style="align-self:end"><button class="btn btn-primary" type="submit" :disabled="pending.roster">{{pending.roster?'Loading…':'Load roster'}}</button></div></form>
        <div v-if="roster" style="margin-top:18px"><div class="report-summary"><strong>{{roster.offering?.course_code}} · Section {{roster.offering?.section_code}}</strong><span>{{roster.roster_count}} student(s)</span></div><DataTable :rows="roster.students||[]" :columns="[{key:'admission_no',label:'Admission no'},{key:'student_name',label:'Student'},{key:'batch',label:'Batch'},{key:'student_status',label:'Student status'},{key:'enrollment_date',label:'Enrolled on'},{key:'enrollment_status',label:'Enrollment'}]"><template #cell-student_status="{value}"><StatusBadge :value="value" /></template><template #cell-enrollment_status="{value}"><StatusBadge :value="value" /></template></DataTable></div>
      </SectionCard>

      <SectionCard title="Student progress report">
        <form class="form-grid form-grid-3" @submit.prevent="loadStudent"><div class="field"><label>Student</label><select v-model="form.student_id" class="select" required><option value="" disabled>Select student</option><option v-for="s in students" :key="s.student_id" :value="s.student_id">{{s.student_name}} · {{s.admission_no}}</option></select></div><div class="field"><label>Semester</label><select v-model="form.semester_id" class="select" required><option value="" disabled>Select semester</option><option v-for="s in semesters" :key="s.semester_id" :value="s.semester_id">{{s.semester_name}} · {{s.academic_year}}</option></select></div><div class="field" style="align-self:end"><button class="btn btn-primary" type="submit" :disabled="pending.student">{{pending.student?'Loading…':'Load student report'}}</button></div></form>
      </SectionCard>

      <template v-if="progress || studentExams || studentGpa">
        <div class="page-heading compact-heading"><div><div class="eyebrow">Selected student</div><h2>{{selectedStudent?.student_name || progress?.student?.student_name}}</h2><p>{{progress?.semester?.semester_name}} · {{progress?.semester?.academic_year}}</p></div></div>
        <div class="stats-grid"><StatCard label="SGPA" :value="progress?.sgpa ?? '—'" icon="S" /><StatCard label="CGPA" :value="progress?.cgpa ?? studentGpa?.cgpa ?? '—'" icon="C" /><StatCard label="Courses" :value="progress?.course_count ?? 0" icon="▦" /><StatCard label="Upcoming exams" :value="examRows.length" icon="◷" /></div>
        <div class="grid grid-2"><SectionCard title="Course performance"><BarChart :items="progressChart" :max="100" suffix="%" /></SectionCard><SectionCard title="Attendance by course"><BarChart :items="attendanceChart" :max="100" suffix="%" /></SectionCard></div>
        <SectionCard title="Course progress"><DataTable :rows="progressRows" :columns="[{key:'course_code',label:'Course'},{key:'course_name',label:'Name'},{key:'credits',label:'Credits'},{key:'course_percentage',label:'Course %'},{key:'attendance_percentage',label:'Attendance %'},{key:'grade_code',label:'Grade'},{key:'grade_point',label:'Point'},{key:'enrollment_status',label:'Enrollment'}]"><template #cell-enrollment_status="{value}"><StatusBadge :value="value" /></template></DataTable></SectionCard>
        <div class="grid grid-2"><SectionCard title="SGPA history"><BarChart :items="gpaChart" :max="10" /></SectionCard><SectionCard title="GPA semesters"><DataTable :rows="gpaRows" :columns="[{key:'semester_name',label:'Semester'},{key:'academic_year',label:'Academic year'},{key:'sgpa',label:'SGPA'},{key:'graded_course_count',label:'Courses'},{key:'graded_credits',label:'Credits'},{key:'verification',label:'Verification'}]"><template #cell-verification="{value}"><StatusBadge :value="value" /></template></DataTable></SectionCard></div>
        <div class="grid grid-2 calendar-table-grid"><CalendarMonth :events="examEvents" title="Student exam calendar" /><SectionCard title="Upcoming exams"><DataTable :rows="examRows" :columns="[{key:'course_code',label:'Course'},{key:'course_name',label:'Course name'},{key:'exam_title',label:'Exam'},{key:'exam_type',label:'Type'},{key:'exam_date',label:'Date'},{key:'start_time',label:'Start'},{key:'end_time',label:'End'}]" /></SectionCard></div>
      </template>
    </template>
  </AppShell>
</template>
