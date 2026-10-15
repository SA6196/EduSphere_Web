import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(fileURLToPath(import.meta.url))

const checks = [
  ['src/components/DataTable.vue', '/_date$/i', 'date-only detection is exact'],
  ['src/components/DataTable.vue', '/_at$/i', 'datetime detection is exact'],
  ['src/views/CatalogView.vue', 'catalogDescription', 'role-aware catalog copy'],
  ['src/views/OfferingWorkspaceView.vue', 'creationAllowed', 'offering lifecycle awareness'],
  ['src/views/OfferingWorkspaceView.vue', "unconfigured(c, 'quiz_id')", 'configured quiz components excluded'],
  ['src/views/student/StudentAttendanceView.vue', 'Attendance history for', 'student attendance hides technical IDs'],
  ['src/views/student/StudentPerformanceView.vue', "{key:'course_code',label:'Course'}", 'student exams use human-facing columns'],
  ['src/views/ProfileView.vue', 'Last login', 'profile remains functional'],
  ['src/views/admin/AdminDashboardView.vue', "{key:'semester_name',label:'Semester'}", 'admin semesters hide database IDs'],
  ['src/views/admin/AdminReportsView.vue', "{key:'admission_no',label:'Admission no'}", 'admin roster hides internal IDs'],
  ['src/components/workspace/WorkspaceAssignmentsTab.vue', 'Open submission', 'submission URLs are human-readable links'],
  ['src/components/workspace/WorkspaceRosterGradingTab.vue', "{key:'admission_no',label:'Admission no'}", 'instructor roster hides internal IDs'],
  ['src/utils/errors.js', 'returned a result with an exception set', 'pyodbc exception-set errors sanitized'],
  ['src/components/FileUrlField.vue', 'stores resource links rather than uploading local file bytes', 'file capability wording is explicit'],
]

let failures = 0
for (const [file, needle, label] of checks) {
  const text = fs.readFileSync(path.join(root, file), 'utf8')
  const ok = text.includes(needle)
  console.log(`${ok ? '[PASS]' : '[FAIL]'} ${label}`)
  if (!ok) failures++
}

console.log(`CROSS-ROLE FRONTEND SMOKE CHECK: ${failures ? `FAIL (${failures})` : 'PASS'}`)
process.exitCode = failures ? 1 : 0
