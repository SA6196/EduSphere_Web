import { reactive } from 'vue'
import { userMessage } from '../utils/errors.js'

const state = reactive({ items: [] })
let nextId = 1

function push(message, type = 'info', timeout = 4200) {
  const normalized = type === 'error' ? userMessage(message, 'Something went wrong.') : String(message ?? '')
  const duplicate = state.items.find((item) => item.type === type && item.message === normalized)
  if (duplicate) return duplicate.id

  const id = nextId++
  state.items.push({ id, message: normalized, type })
  if (timeout) setTimeout(() => remove(id), timeout)
  return id
}

function remove(id) {
  const index = state.items.findIndex((item) => item.id === id)
  if (index >= 0) state.items.splice(index, 1)
}

export const toast = {
  state,
  success: (m) => push(m, 'success'),
  error: (m) => push(m, 'error', 7000),
  info: (m) => push(m, 'info'),
  remove,
}
