<script setup>
import { computed, ref, watch } from 'vue'
import {
  clampInteger, makeStatusCounts, scoreAttendance,
  predictAttendance, buildProjectionPoints,
} from '../utils/attendancePredictor.js'

const props = defineProps({
  courses: { type: Array, default: () => [] },
  sessions: { type: Array, default: () => [] },
})

const selectedCourseId = ref('')
const latePolicy = ref('present')
const excusedPolicy = ref('absent')
const target = ref(75)
const futureClasses = ref(10)
const futureMissed = ref(0)

const courseRows = computed(() => props.courses.map(course => {
  const sessions = props.sessions.filter(s => String(s.offering_id) === String(course.offering_id))
  const counts = makeStatusCounts(sessions)
  // Oracle FN_ATTENDANCE_PCT is the authoritative percentage; controls affect projections only.
  const totalRecorded = counts.PRESENT + counts.ABSENT + counts.LATE + counts.EXCUSED
  const official = totalRecorded ? Number(course.official_attendance_pct) : null
  const officialPercentage = official != null && Number.isFinite(official) ? official : null
  return { ...course, counts, officialPercentage, ...scoreAttendance(counts, latePolicy.value, excusedPolicy.value) }
}))

watch(courseRows, rows => {
  if (!rows.some(course => String(course.offering_id) === selectedCourseId.value)) {
    selectedCourseId.value = rows.length ? String(rows[0].offering_id) : ''
  }
}, { immediate: true })
const chosen = computed(() => courseRows.value.find(course => String(course.offering_id) === selectedCourseId.value) || null)
const planning = computed(() => predictAttendance(chosen.value?.attended, chosen.value?.eligible, futureClasses.value, futureMissed.value, target.value))
const points = computed(() => chosen.value ? buildProjectionPoints(chosen.value.attended, chosen.value.eligible, planning.value.future, planning.value.missed) : [])
const totalRecorded = computed(() => chosen.value ? ['PRESENT', 'ABSENT', 'LATE', 'EXCUSED'].reduce((total, s) => total + chosen.value.counts[s], 0) : 0)
const donutStyle = computed(() => {
  if (!chosen.value || !totalRecorded.value) return { background: 'var(--border, #e2e8f0)' }
  const colors = { PRESENT: '#16a34a', ABSENT: '#ef4444', LATE: '#f59e0b', EXCUSED: '#64748b' }
  let start = 0
  const stops = []
  for (const status of ['PRESENT', 'ABSENT', 'LATE', 'EXCUSED']) {
    const end = start + 100 * chosen.value.counts[status] / totalRecorded.value
    if (end > start) stops.push(`${colors[status]} ${start}% ${end}%`)
    start = end
  }
  return { background: `conic-gradient(${stops.join(', ')})` }
})
const formatRate = value => value == null ? 'Not available' : `${value.toFixed(1)}%`
const pointX = step => 48 + step * 548 / Math.max(1, planning.value.future)
const pointY = percentage => 204 - Math.max(0, Math.min(100, percentage)) * 1.72
const polyline = key => points.value.map(point => `${pointX(point.step).toFixed(2)},${pointY(point[key]).toFixed(2)}`).join(' ')
const policyOptions = [
  { value: 'exclude', label: 'Exclude from calculation' },
  { value: 'present', label: 'Count as present' },
  { value: 'absent', label: 'Count as absent' },
]
</script>

<template>
  <section class="analytics-root" aria-label="Attendance charts and predictor">
    <div class="analytics-heading">
      <div><h2>Attendance insights</h2><p>Based only on your instructor-recorded sessions in this semester.</p></div>
      <span class="insight-tag">Interactive</span>
    </div>

    <div class="policy-panel">
      <div class="policy-title"><strong>Percentage calculation rules</strong><span>What-if assumptions for the predictor</span></div>
      <label>Late attendance
        <select v-model="latePolicy" class="select"><option v-for="option in policyOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select>
      </label>
      <label>Excused attendance
        <select v-model="excusedPolicy" class="select"><option v-for="option in policyOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select>
      </label>
      <p class="policy-hint">The official Oracle rule is (Present + Late) ÷ (Present + Absent + Late + Excused). The controls change only the hypothetical predictor, not official marks or attendance records.</p>
    </div>

    <div class="analytics-grid">
      <section class="insight-card" aria-label="Course-wise attendance percentage chart">
        <div class="card-head"><h3>Attendance by course</h3><span>Recorded classes</span></div>
        <div v-if="!courseRows.length" class="empty-chart">No courses for this semester.</div>
        <div v-else class="course-chart">
          <div v-for="course in courseRows" :key="course.offering_id" class="course-bar-row">
            <div class="course-bar-heading"><span :title="course.course_name">{{ course.course_code }}</span><strong>{{ formatRate(course.officialPercentage) }}</strong></div>
            <div class="chart-track" role="meter" :aria-label="`${course.course_code} attendance percentage`" :aria-valuemin="0" :aria-valuemax="100" :aria-valuenow="course.officialPercentage == null ? undefined : Math.round(course.officialPercentage)">
              <div class="chart-fill" :class="{ 'below-target': course.officialPercentage != null && course.officialPercentage < planning.target }" :style="{ width: `${course.officialPercentage ?? 0}%` }"></div>
              <i class="threshold-tick" :style="{ left: `${planning.target}%` }" aria-hidden="true"></i>
            </div>
            <small>{{ course.eligible }} counted of {{ course.counts.PRESENT + course.counts.ABSENT + course.counts.LATE + course.counts.EXCUSED }} recorded</small>
          </div>
          <p class="chart-footnote">Bars use the official Oracle attendance function; vertical ticks mark your planning target. A missing rate means no recorded attendance.</p>
        </div>
      </section>

      <section class="insight-card" aria-label="Attendance status distribution chart">
        <div class="card-head"><h3>Recorded status breakdown</h3><span>Choose a course below</span></div>
        <label class="course-picker">Course
          <select v-model="selectedCourseId" class="select">
            <option v-for="course in courseRows" :key="course.offering_id" :value="String(course.offering_id)">{{ course.course_code }} · {{ course.course_name }}</option>
          </select>
        </label>
        <div v-if="chosen" class="breakdown-layout">
          <div class="donut" :style="donutStyle" role="img" :aria-label="`${chosen.counts.PRESENT} present, ${chosen.counts.ABSENT} absent, ${chosen.counts.LATE} late, ${chosen.counts.EXCUSED} excused recorded sessions`">
            <div class="donut-center"><strong>{{ totalRecorded }}</strong><span>recorded</span></div>
          </div>
          <div class="donut-legend">
            <div v-for="item in [{status:'PRESENT',label:'Present'},{status:'ABSENT',label:'Absent'},{status:'LATE',label:'Late'},{status:'EXCUSED',label:'Excused'}]" :key="item.status" class="legend-line">
              <span class="legend-chip" :class="item.status.toLowerCase()"></span><span>{{ item.label }}</span><strong>{{ chosen.counts[item.status] }}</strong>
            </div>
            <p>{{ chosen.counts.unrecorded }} unrecorded · {{ chosen.counts.upcoming }} upcoming</p>
          </div>
        </div>
        <div v-else class="empty-chart">No course selected.</div>
      </section>
    </div>

    <section class="predictor-card" aria-label="Attendance what-if predictor">
      <div class="card-head"><div><h3>Attendance predictor</h3><p>See how your rate could change after future classes.</p></div><span class="insight-tag">What-if</span></div>
      <div v-if="!chosen" class="empty-chart">Select a course to plan future attendance.</div>
      <template v-else>
        <div class="predictor-controls">
          <label>Target percentage
            <div class="input-unit"><input v-model.number="target" class="input" type="number" min="1" max="100" step="1" aria-label="Attendance percentage target" /><span>%</span></div>
          </label>
          <label>Future classes to simulate
            <input v-model.number="futureClasses" class="input" type="number" min="0" max="120" step="1" />
          </label>
          <label>Classes you might miss
            <input v-model.number="futureMissed" class="input" type="number" min="0" :max="planning.future" step="1" />
          </label>
        </div>
        <p v-if="futureMissed > planning.future || futureClasses !== planning.future || futureMissed < 0 || target !== planning.target" class="field-note">Inputs are calculated using whole-number limits: target 1–100%, classes 0–120, missed 0–future classes.</p>
        <p class="official-rate">Official attendance for this course: <strong>{{ formatRate(chosen.officialPercentage) }}</strong>. Planning inputs below never change the official rate.</p>
        <div class="prediction-stats" aria-live="polite">
          <div><span>What-if starting rate</span><strong>{{ formatRate(planning.current) }}</strong><small>{{ chosen.attended }} / {{ chosen.eligible }} counted sessions</small></div>
          <div class="featured-stat"><span>After your plan</span><strong>{{ formatRate(planning.predicted) }}</strong><small>{{ planning.future - planning.missed }} attended · {{ planning.missed }} missed</small></div>
          <div><span>Consecutive classes to reach {{ planning.target }}%</span><strong>{{ planning.needToAttend == null ? '—' : planning.needToAttend }}</strong><small>{{ planning.current == null ? 'Needs recorded classes' : planning.needToAttend == null ? 'Not reachable by attendance alone at this target' : planning.needToAttend === 0 ? 'Target already met' : 'Attend without missing' }}</small></div>
          <div><span>Extra classes you could miss</span><strong>{{ planning.mayMiss == null ? '—' : planning.mayMiss }}</strong><small>{{ planning.mayMiss == null ? 'Target is not yet met or no records' : 'Before falling below target' }}</small></div>
        </div>
        <div v-if="points.length > 0 && planning.future > 0" class="prediction-plot">
          <svg viewBox="0 0 640 255" role="img" aria-label="Projected attendance percentages after future classes, showing all attended, planned misses, all missed, and target" preserveAspectRatio="xMidYMid meet">
            <g v-for="tick in [0, 25, 50, 75, 100]" :key="tick">
              <line x1="48" :y1="pointY(tick)" x2="596" :y2="pointY(tick)" stroke="currentColor" class="grid-line"/>
              <text x="40" :y="pointY(tick) + 4" text-anchor="end" class="axis-label">{{ tick }}%</text>
            </g>
            <line x1="48" y1="204" x2="596" y2="204" stroke="currentColor" class="axis-line" />
            <line :x1="48" :y1="pointY(planning.target)" :x2="596" :y2="pointY(planning.target)" class="line-target" />
            <polyline :points="polyline('worst')" class="line-worst" />
            <polyline :points="polyline('best')" class="line-best" />
            <polyline v-if="planning.missed > 0" :points="polyline('plan')" class="line-plan" />
            <text x="48" y="227" text-anchor="middle" class="axis-label">0</text>
            <text :x="pointX(Math.floor(planning.future / 2))" y="227" text-anchor="middle" class="axis-label">{{ Math.floor(planning.future / 2) }}</text>
            <text x="596" y="227" text-anchor="middle" class="axis-label">{{ planning.future }}</text>
            <text x="322" y="248" text-anchor="middle" class="axis-label">Future classes</text>
          </svg>
          <div class="plot-legend"><span class="legend-best">All attended · {{ formatRate(planning.best) }}</span><span v-if="planning.missed > 0" class="legend-plan">Your plan · {{ formatRate(planning.predicted) }}</span><span class="legend-worst">All missed · {{ formatRate(planning.worst) }}</span><span class="legend-target">Target · {{ planning.target }}%</span></div>
        </div>
        <p v-else class="chart-footnote">{{ planning.current == null ? 'The graph will appear after at least one qualifying attendance record.' : 'Enter at least one future class to see the projection graph.' }}</p>
        <p class="predictor-disclaimer">Projection only: future class counts and absences are hypothetical, not your timetable. The intermediate planned line distributes absences evenly; the final percentage is exact for your chosen counts. No academic attendance policy is inferred or stored.</p>
      </template>
    </section>
  </section>
</template>

<style scoped>
.analytics-root { margin: 24px 0; display:grid; gap:18px; }
.analytics-heading,.card-head { display:flex; justify-content:space-between; gap:16px; align-items:start; }
.analytics-heading h2 {margin:0;font-size:20px} .analytics-heading p,.card-head p {margin:4px 0 0;color:var(--text-muted,#64748b);font-size:13px}
.insight-tag { padding:5px 10px;border-radius:999px;background:#eaf4ff;color:#1d4ed8;font-size:11px;font-weight:750;white-space:nowrap; }
.policy-panel { border-radius:12px; border:1px solid var(--border,#e2e8f0);background:var(--surface-subtle,#f8fafc);display:grid;grid-template-columns:minmax(190px,1fr) minmax(170px,1fr) minmax(170px,1fr);gap:12px 18px;padding:18px;align-items:end; }
.policy-title{align-self:center;display:grid;gap:3px}.policy-title span{font-size:12px;color:var(--text-muted,#64748b)}
.policy-panel label,.course-picker,.predictor-controls label{display:grid;gap:6px;font-size:12px;font-weight:700;min-width:0}.policy-panel .select,.course-picker .select{width:100%;font-size:13px}
.policy-hint{font-size:12px;color:var(--text-muted,#64748b);margin:0;grid-column:1/-1;line-height:1.5}
.analytics-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.insight-card,.predictor-card{border:1px solid var(--border,#e2e8f0);border-radius:14px;background:var(--surface,#fff);padding:20px;min-width:0}
.card-head{align-items:center;margin-bottom:20px}.card-head h3{font-size:16px;margin:0}.card-head>span{font-size:12px;color:var(--text-muted,#64748b)}
.course-chart{display:grid;gap:15px}.course-bar-heading{display:flex;justify-content:space-between;gap:10px;font-size:13px}.course-bar-heading strong{white-space:nowrap}.chart-track{height:12px;position:relative;border-radius:999px;background:#e8eef5;overflow:visible}.chart-fill{background:#0f9c7a;height:100%;border-radius:999px;transition:width .25s ease}.chart-fill.below-target{background:#f59e0b}.threshold-tick{position:absolute;top:-4px;height:20px;border-left:2px dashed #334155;opacity:.7}.course-bar-row small{display:block;color:var(--text-muted,#64748b);font-size:11px;margin-top:4px}.chart-footnote,.predictor-disclaimer,.field-note{font-size:12px;line-height:1.55;color:var(--text-muted,#64748b);margin:5px 0}.empty-chart{padding:25px 5px;color:var(--text-muted,#64748b);font-size:13px}
.course-picker{margin-bottom:18px}.breakdown-layout{display:flex;gap:26px;align-items:center;justify-content:center;flex-wrap:wrap}.donut{width:170px;height:170px;border-radius:50%;display:grid;place-items:center;flex-shrink:0}.donut-center{width:112px;height:112px;border-radius:50%;background:var(--surface,#fff);display:flex;flex-direction:column;align-items:center;justify-content:center}.donut-center strong{font-size:27px}.donut-center span{font-size:12px;color:var(--text-muted,#64748b)}.donut-legend{flex:1;min-width:160px;display:grid;gap:10px}.legend-line{display:grid;grid-template-columns:12px 1fr auto;gap:9px;align-items:center;font-size:13px}.legend-chip{width:11px;height:11px;border-radius:3px}.legend-chip.present{background:#16a34a}.legend-chip.absent{background:#ef4444}.legend-chip.late{background:#f59e0b}.legend-chip.excused{background:#64748b}.donut-legend p{font-size:11px;color:var(--text-muted,#64748b);margin:2px 0 0}
.predictor-controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:17px}.predictor-controls .input{width:100%;box-sizing:border-box}.input-unit{display:flex;align-items:center;position:relative}.input-unit .input{padding-right:29px}.input-unit span{position:absolute;right:12px;color:var(--text-muted,#64748b)}
.prediction-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.prediction-stats>div{display:flex;flex-direction:column;gap:7px;padding:16px;border:1px solid var(--border,#e2e8f0);border-radius:11px;min-width:0}.prediction-stats span{font-size:12px;color:var(--text-muted,#64748b);font-weight:650}.prediction-stats strong{font-size:24px;letter-spacing:-.5px}.prediction-stats small{font-size:11px;color:var(--text-muted,#64748b)}.featured-stat{background:#ecfdf5;border-color:#a7f3d0!important;color:#065f46}
.prediction-plot{max-width:850px;margin:22px auto 0}.prediction-plot svg{width:100%;height:auto;display:block;overflow:visible;color:#64748b}.axis-label{fill:currentColor;font-size:12px}.grid-line{opacity:.16}.axis-line{opacity:.6}.line-best,.line-worst,.line-plan,.line-target{fill:none;stroke-linecap:round;stroke-linejoin:round}.line-best{stroke:#16a34a;stroke-width:3}.line-plan{stroke:#2563eb;stroke-width:3}.line-worst{stroke:#ef4444;stroke-width:2.5}.line-target{stroke:#64748b;stroke-width:1.7;stroke-dasharray:6 5}.plot-legend{display:flex;gap:12px 22px;flex-wrap:wrap;justify-content:center;font-size:12px;margin-bottom:14px}.plot-legend span::before{content:' ';display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:7px;background:currentColor}.legend-best{color:#16a34a}.legend-plan{color:#2563eb}.legend-worst{color:#ef4444}.legend-target{color:#64748b}
.predictor-disclaimer{margin-top:13px}.official-rate{font-size:13px;color:var(--text-muted,#64748b);margin:5px 0 16px}.official-rate strong{color:var(--text-primary,#0f172a)}
@media(max-width:1000px){.policy-panel{grid-template-columns:1fr 1fr}.policy-title{grid-column:1/-1}.prediction-stats{grid-template-columns:repeat(2,1fr)}}
@media(max-width:720px){.analytics-grid{grid-template-columns:1fr}.predictor-controls{grid-template-columns:1fr}.policy-panel{grid-template-columns:1fr}.policy-title{grid-column:auto}.prediction-stats{grid-template-columns:1fr 1fr}.insight-card,.predictor-card{padding:15px}.donut{width:150px;height:150px}.donut-center{width:99px;height:99px}}
@media(max-width:430px){.prediction-stats{grid-template-columns:1fr}.analytics-heading{flex-wrap:wrap}}
</style>
