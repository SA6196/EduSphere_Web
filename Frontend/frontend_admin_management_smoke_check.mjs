import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// Use fileURLToPath for correct cross-platform path resolution (handles Windows spaces and drive letters).
const root = path.dirname(fileURLToPath(import.meta.url))

const checks = [
  ['admin route', 'src/router/index.js', '/admin/management'],
  ['admin nav item', 'src/components/AppShell.vue', 'Academic Setup'],
  ['admin API directory', 'src/services/api.js', "directory: () => request('/admin/manage/directory/')"],
  ['student creation API', 'src/services/api.js', 'createStudent:'],
  ['instructor creation API', 'src/services/api.js', 'createInstructor:'],
  ['offering creation API', 'src/services/api.js', 'createOffering:'],
  ['grading API', 'src/services/api.js', 'saveGrading:'],
  ['management tabs', 'src/views/admin/AdminManagementView.vue', "key: 'grading'"],
  ['student form', 'src/views/admin/AdminManagementView.vue', 'Create student account'],
  ['instructor form', 'src/views/admin/AdminManagementView.vue', 'Create instructor account'],
  ['class offering form', 'src/views/admin/AdminManagementView.vue', 'Create class'],
  ['instructor assignments', 'src/views/admin/AdminManagementView.vue', 'Save instructor assignments'],
  ['weight total', 'src/views/admin/AdminManagementView.vue', 'Total weight:'],
  ['published-grade lock', 'src/views/admin/AdminManagementView.vue', 'final course grade(s) have already been published'],
]
let failed = 0
for (const [label, rel, needle] of checks) {
  const file = path.join(root, rel)
  const ok = fs.existsSync(file) && fs.readFileSync(file, 'utf8').includes(needle)
  console.log(`[${ok ? 'PASS' : 'FAIL'}] ${label}`)
  if (!ok) failed++
}
if (failed) { console.error(`ADMIN MANAGEMENT FRONTEND SMOKE: FAIL (${failed})`); process.exit(1) }
console.log('ADMIN MANAGEMENT FRONTEND SMOKE: PASS')
