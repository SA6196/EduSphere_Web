import { reactive, computed } from 'vue'
import { api } from '../services/api.js'
import { clearTokens, getAccessToken, setTokens } from '../services/http.js'

const USER_KEY = 'edusphere_user'

const state = reactive({
  user: null,
  ready: false,
  loading: false,
})

function loadStoredUser() {
  try {
    const raw = sessionStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function persistUser(user) {
  state.user = user
  if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user))
  else sessionStorage.removeItem(USER_KEY)
}

async function bootstrap() {
  state.user = loadStoredUser()
  if (getAccessToken()) {
    try {
      const user = await api.auth.me()
      persistUser(user)
    } catch {
      logout(false)
    }
  }
  state.ready = true
}

async function login(username, password) {
  state.loading = true
  try {
    const result = await api.auth.login(username, password)
    setTokens({ access: result.access, refresh: result.refresh })
    persistUser(result.user)
    return result.user
  } finally {
    state.loading = false
  }
}

function logout(redirect = true) {
  clearTokens()
  persistUser(null)
  if (redirect && window.location.pathname !== '/login') window.location.assign('/login')
}

window.addEventListener('edusphere:auth-expired', () => logout())

export const auth = {
  state,
  user: computed(() => state.user),
  role: computed(() => state.user?.role || null),
  isAuthenticated: computed(() => Boolean(state.user && getAccessToken())),
  bootstrap,
  login,
  logout,
}
