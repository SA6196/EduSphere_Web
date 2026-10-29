import { normalizeApiError } from '../utils/errors.js'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '')
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 20000)

const ACCESS_KEY = 'edusphere_access'
const REFRESH_KEY = 'edusphere_refresh'
let refreshPromise = null
// Only concurrent, identical GETs are combined. Never cache across requests,
// and never coalesce mutations or abortable reads.
const pendingGets = new Map()

export function getAccessToken() {
  return sessionStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken() {
  return sessionStorage.getItem(REFRESH_KEY)
}

export function setTokens({ access, refresh }) {
  if (access) sessionStorage.setItem(ACCESS_KEY, access)
  if (refresh) sessionStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS_KEY)
  sessionStorage.removeItem(REFRESH_KEY)
  pendingGets.clear()
}

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    try { return await response.json() }
    catch { return { message: 'The server returned an unreadable response.' } }
  }
  const text = await response.text()
  return text ? { message: text } : {}
}

async function doRefreshAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) return false

  let response
  try {
    response = await fetch(`${API_BASE}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
  } catch {
    return false
  }

  if (!response.ok) return false
  let body
  try { body = await response.json() } catch { return false }
  if (!body?.access) return false
  setTokens({ access: body.access })
  return true
}

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = doRefreshAccessToken().finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

function makeClientError(message, { status = 0, code = null, kind = 'client', body = null, serverMessage = '', oracleCode = null } = {}) {
  const error = new Error(message)
  error.status = status
  error.code = code
  error.kind = kind
  error.body = body
  error.serverMessage = serverMessage
  error.oracleCode = oracleCode
  return error
}

function combineAbortSignals(controller, externalSignal) {
  if (!externalSignal) return
  if (externalSignal.aborted) {
    controller.abort(externalSignal.reason)
    return
  }
  externalSignal.addEventListener('abort', () => controller.abort(externalSignal.reason), { once: true })
}

export function request(path, options = {}, retry = true) {
  const method = String(options.method || 'GET').toUpperCase()
  const canCombine = retry && method === 'GET' && !options.signal &&
    !options.body && !options.headers && !options.timeoutMs
  if (!canCombine) return performRequest(path, options, retry)

  // Include the access token to avoid sharing responses across logins.
  const url = path.startsWith('http') ? path : `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
  const key = `${getAccessToken() || ''}\u0000${url}`
  if (pendingGets.has(key)) return pendingGets.get(key)
  const job = performRequest(path, options, retry)
  pendingGets.set(key, job)
  // Cleanup for both resolve and reject without creating an unhandled promise.
  void job.then(
    () => { if (pendingGets.get(key) === job) pendingGets.delete(key) },
    () => { if (pendingGets.get(key) === job) pendingGets.delete(key) },
  )
  return job
}

async function performRequest(path, options = {}, retry = true) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
  const headers = new Headers(options.headers || {})
  const access = getAccessToken()

  if (access) headers.set('Authorization', `Bearer ${access}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const controller = new AbortController()
  combineAbortSignals(controller, options.signal)
  const timeoutMs = Number(options.timeoutMs ?? DEFAULT_TIMEOUT_MS)
  const timeout = timeoutMs > 0 ? setTimeout(() => controller.abort('timeout'), timeoutMs) : null

  let response
  try {
    response = await fetch(url, { ...options, headers, signal: controller.signal })
  } catch (cause) {
    if (timeout) clearTimeout(timeout)
    const timedOut = controller.signal.aborted && controller.signal.reason === 'timeout'
    if (timedOut) {
      throw makeClientError('The request took too long. Please try again.', { status: 408, kind: 'timeout' })
    }
    if (cause?.name === 'AbortError') {
      throw makeClientError('The request was cancelled.', { kind: 'cancelled' })
    }
    throw makeClientError(
      navigator.onLine === false
        ? 'You appear to be offline. Check your internet connection and try again.'
        : 'Could not reach the EduSphere backend. Make sure the Django server is running and try again.',
      { kind: 'network' },
    )
  }
  if (timeout) clearTimeout(timeout)

  const body = await parseResponse(response)

  if (response.status === 401 && retry && getRefreshToken()) {
    const refreshed = await refreshAccessToken()
    if (refreshed) return request(path, options, false)
  }

  if (!response.ok) {
    const normalized = normalizeApiError({ body, status: response.status, fallback: `Request failed (${response.status})` })
    const error = makeClientError(normalized.message, {
      status: response.status,
      code: normalized.backendCode,
      kind: response.status >= 500 ? 'server' : 'api',
      body,
      serverMessage: normalized.serverMessage,
      oracleCode: normalized.oracleCode,
    })
    if (response.status === 401) {
      clearTokens()
      window.dispatchEvent(new CustomEvent('edusphere:auth-expired'))
    }
    throw error
  }

  return body
}

export function unwrap(body) {
  if (body && typeof body === 'object' && Object.prototype.hasOwnProperty.call(body, 'success') && Object.prototype.hasOwnProperty.call(body, 'data')) {
    return body.data
  }
  return body
}

export { API_BASE }
