import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const required = [
  'package.json','index.html','src/main.js','src/App.vue','src/router/index.js',
  'src/services/http.js','src/services/api.js','src/stores/auth.js',
  'src/components/DataTable.vue','src/components/ConfirmDialog.vue','src/components/LoadingState.vue',
  'src/components/BarChart.vue','src/components/CalendarMonth.vue','src/components/FileUrlField.vue',
  'src/components/workspace/WorkspaceOverviewTab.vue','src/components/workspace/WorkspaceMaterialsTab.vue',
  'src/components/workspace/WorkspaceAnnouncementsTab.vue','src/components/workspace/WorkspaceSessionsTab.vue',
  'src/components/workspace/WorkspaceAssignmentsTab.vue','src/components/workspace/WorkspaceQuizzesTab.vue',
  'src/components/workspace/WorkspaceExamsTab.vue','src/components/workspace/WorkspaceAttendanceTab.vue',
  'src/components/workspace/WorkspaceRosterGradingTab.vue','src/components/workspace/WorkspaceRecordAttendanceTab.vue',
  'src/views/LoginView.vue','src/views/CatalogView.vue','src/views/OfferingWorkspaceView.vue',
  'src/views/student/StudentDashboardView.vue','src/views/student/StudentPerformanceView.vue','src/views/student/StudentAttendanceView.vue','src/views/student/QuizAttemptView.vue',
  'src/views/instructor/InstructorDashboardView.vue','src/views/instructor/QuestionBankView.vue',
  'src/views/admin/AdminDashboardView.vue','src/views/admin/AdminReportsView.vue',
  'FRONTEND_LIMITATIONS_V2.md'
]
let failures = 0
for (const file of required) {
  const ok = fs.existsSync(path.join(root, file))
  console.log(`${ok ? '[PASS]' : '[FAIL]'} ${file}`)
  if (!ok) failures++
}

const checks = [
  ['src/views/CatalogView.vue', 'studentDashboard()', 'catalog enrollment awareness'],
  ['src/views/OfferingWorkspaceView.vue', 'WorkspaceRosterGradingTab', 'workspace component split'],
  ['src/views/student/StudentPerformanceView.vue', 'Semester-wise marks view', 'student semester-first marks'],
  ['src/views/student/StudentAttendanceView.vue', 'Select Semester', 'student semester-wise attendance'],
  ['src/views/admin/AdminReportsView.vue', 'Select student', 'admin named student selector'],
  ['src/views/student/QuizAttemptView.vue', 'Time remaining', 'quiz countdown'],
  ['src/views/student/QuizAttemptView.vue', 'sessionStorage', 'quiz local draft'],
  ['src/components/DataTable.vue', 'toggleSort', 'table sorting'],
  ['src/components/FileUrlField.vue', 'stores resource links rather than uploading local file bytes', 'file capability honesty'],
]
for (const [file, needle, label] of checks) {
  const text = fs.readFileSync(path.join(root, file), 'utf8')
  const ok = text.includes(needle)
  console.log(`${ok ? '[PASS]' : '[FAIL]'} ${label}`)
  if (!ok) failures++
}

const api = fs.readFileSync(path.join(root, 'src/services/api.js'), 'utf8')
const endpoints = [
  '/auth/login/','/student/dashboard/','/instructor/offerings/','/admin/summary/',
  '/offerings/${id}/grading/','/attendance/sessions/','/assignments/create/',
  '/materials/create/','/announcements/create/','/quizzes/${quizId}/content/',
  '/quizzes/questions/','/quizzes/attempt/${attemptId}/result/','/exams/schedule/',
  '/gpa/my/','/reports/admin/overview/'
]
for (const e of endpoints) {
  const ok = api.includes(e)
  console.log(`${ok ? '[PASS]' : '[FAIL]'} endpoint ${e}`)
  if (!ok) failures++
}
console.log(`FRONTEND UX SMOKE CHECK: ${failures ? `FAIL (${failures})` : 'PASS'}`)
process.exitCode = failures ? 1 : 0
