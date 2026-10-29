import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
const catalog=readFileSync(new URL('./src/views/CatalogView.vue',import.meta.url),'utf8')
const api=readFileSync(new URL('./src/services/api.js',import.meta.url),'utf8')
const script=catalog.match(/<script setup>([\s\S]*?)<\/script>/)?.[1]
test('Vue script and API JavaScript pass JS syntax checks', () => {
 assert.ok(script)
 for (const src of [script,api]) {
  const p=spawnSync(process.execPath,['--check','--input-type=module'],{input:src,encoding:'utf8'})
  assert.equal(p.status,0,p.stderr)
 }
})
test('only students with ENROLLED status and OPEN offering can drop',()=>{
 assert.match(catalog,/role\.value === 'STUDENT' && o\.offering_status === 'OPEN' && existing\(o\)\?\.enrollment_status === 'ENROLLED'/)
})
test('student must confirm via danger dialog',()=>{
 assert.match(catalog,/title="Drop this course\?"/)
 assert.match(catalog,/confirm-label="Drop Course" tone="danger"/)
 assert.match(catalog,/@confirm="confirmDrop"/)
})
test('drop endpoint uses POST and does not include student ID',()=>{
 assert.match(api,/dropCourse: \(offeringId\) => request\(`\/enrollments\/\$\{offeringId\}\/drop\/`, \{ method: 'POST' \}/)
 assert.doesNotMatch(api,/dropCourse:[^\n]*studentId/)
})
test('successful drop refreshes state and provides feedback',()=>{
 assert.match(catalog,/await api\.academics\.dropCourse\(o\.offering_id\)/)
 assert.match(catalog,/toast\.success\(`Dropped/)
 assert.match(catalog,/await load\(\)/)
})
test('dropped courses display Withdrawn and no longer open workspace',()=>{
 assert.match(catalog,/existing\(o\)\.enrollment_status === 'DROPPED' \? 'Withdrawn'/)
 assert.match(catalog,/canOpenWorkspace\(o\)/)
})
test('existing enrollment confirmation stays available',()=>{
 assert.match(catalog,/title="Confirm enrollment"/)
 assert.match(catalog,/confirmEnroll/)
})
