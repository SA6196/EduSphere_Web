import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const file = new URL('./src/services/http.js', import.meta.url)
const source = readFileSync(file, 'utf8')
  .replace("import { normalizeApiError } from '../utils/errors.js'", "const normalizeApiError = ({status}) => ({message: `HTTP ${status}`})")
  .replaceAll('import.meta.env', '{}')
const client = await import(`data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`)
const tokens = new Map()
globalThis.sessionStorage = {
  getItem: k => tokens.get(k) || null,
  setItem: (k, v) => tokens.set(k, v),
  removeItem: k => tokens.delete(k),
}

const response = (value) => ({
  status: 200,
  ok: true,
  headers: { get: () => 'application/json' },
  json: async () => ({ success: true, data: value }),
})

test('identical concurrent GET requests share one network request', async () => {
  let count = 0
  globalThis.fetch = async () => { count++; await new Promise(resolve => setTimeout(resolve, 20)); return response(1) }
  const a = client.request('/student/dashboard/')
  const b = client.request('/student/dashboard/')
  assert.equal(a, b)
  await Promise.all([a, b])
  assert.equal(count, 1)
  await client.request('/student/dashboard/')
  assert.equal(count, 2) // no persistent cache / no stale marks
})

test('POSTs must never be deduplicated', async () => {
  let count = 0
  globalThis.fetch = async () => { count++; await new Promise(resolve => setTimeout(resolve, 5)); return response(1) }
  await Promise.all([
    client.request('/quizzes/attempt/1/submit/', {method:'POST'}),
    client.request('/quizzes/attempt/1/submit/', {method:'POST'}),
  ])
  assert.equal(count, 2)
})

test('different login access tokens never share responses', async () => {
  let count = 0
  globalThis.fetch = async () => { count++; await new Promise(resolve => setTimeout(resolve, 15)); return response(1) }
  client.setTokens({access:'student1'})
  const a = client.request('/marks/my/')
  client.setTokens({access:'student2'})
  const b = client.request('/marks/my/')
  await Promise.all([a,b])
  assert.equal(count,2)
  client.clearTokens()
})

test('an abortable GET is never coalesced', async () => {
  let count = 0
  globalThis.fetch = async () => { count++; await new Promise(resolve => setTimeout(resolve, 5)); return response(1) }
  const ctrl = new AbortController()
  await Promise.all([
    client.request('/attendance/my/', {signal:ctrl.signal}),
    client.request('/attendance/my/', {signal:ctrl.signal}),
  ])
  assert.equal(count,2)
})
