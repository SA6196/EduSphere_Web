import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
const view = readFileSync(new URL('./src/views/student/QuizAttemptView.vue', import.meta.url), 'utf8')
const api = readFileSync(new URL('./src/services/api.js', import.meta.url), 'utf8')
const script = view.match(/<script setup>([\s\S]*?)<\/script>/)?.[1]
test('Vue script and API JS parse', () => {
  assert.ok(script)
  for (const source of [script, api]) {
    const p = spawnSync(process.execPath, ['--check', '--input-type=module'], { input: source, encoding: 'utf8' })
    assert.equal(p.status, 0, p.stderr)
  }
})
test('retrieve pending attempt before starting another', () => {
  assert.match(view, /pending=await api\.quizzes\.pendingAttempt\(quizId\.value\)/)
  assert.ok(view.indexOf('pending=await api.quizzes.pendingAttempt') < view.indexOf('const started=await api.quizzes.startAttempt'))
})
test('uses secure authenticated pending endpoint', () => {
  assert.match(api, /pendingAttempt: \(quizId\) => request\(`\/quizzes\/\$\{quizId\}\/pending\/`\)/)
})
test('expired attempts cannot read or edit answers from recovery screen', () => {
  assert.match(view, /Only answers already saved to EduSphere can be submitted/)
  const body = view.split('async function finalizePending(){')[1].split('async function transmitQuestion(q)')[0]
  assert.match(body, /api\.quizzes\.submitAttempt\(id\)/)
  assert.doesNotMatch(body, /api\.quizzes\.response|transmitQuestion/)
})
test('finalize button and feedback appear for pending attempt', () => {
  assert.match(view, /v-else-if="pendingAttempt"/)
  assert.match(view, /Finalize saved attempt/)
  assert.match(view, /pendingError\.value=e\.message/)
})
test('original quiz content and normal submission flows remain', () => {
  assert.match(view, /api\.quizzes\.content\(quizId\.value\)/)
  assert.match(view, /async function submitQuiz\(auto=false\)/)
  assert.match(view, /await api\.quizzes\.submitAttempt\(attemptId\.value\)/)
})
