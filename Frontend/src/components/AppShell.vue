<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { auth } from '../stores/auth.js'

const mobileOpen = ref(false)
const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const route = useRoute()

function setOnline() { online.value = true }
function setOffline() { online.value = false }
onMounted(() => { window.addEventListener('online', setOnline); window.addEventListener('offline', setOffline) })
onUnmounted(() => { window.removeEventListener('online', setOnline); window.removeEventListener('offline', setOffline) })

const items = computed(() => {
  const role = auth.state.user?.role
  if (role === 'STUDENT') return [
    { to: '/student/dashboard', label: 'Dashboard', icon: '⌂' },
    { to: '/catalog', label: 'Course Catalog', icon: '▦' },
    { to: '/student/performance', label: 'Performance', icon: '↗' },
    { to: '/student/attendance', label: 'Attendance', icon: '▤' },
    { to: '/student/quiz-attempts', label: 'Quiz Attempts', icon: '✓' },
    { to: '/profile', label: 'My Profile', icon: '○' },
  ]
  if (role === 'INSTRUCTOR') return [
    { to: '/instructor/dashboard', label: 'Dashboard', icon: '⌂' },
    { to: '/catalog', label: 'Course Catalog', icon: '▦' },
    { to: '/question-bank', label: 'Question Bank', icon: '?' },
    { to: '/profile', label: 'My Profile', icon: '○' },
  ]
  return [
    { to: '/admin/dashboard', label: 'Dashboard', icon: '⌂' },
    { to: '/admin/reports', label: 'Reports', icon: '▤' },
    { to: '/admin/management', label: 'Academic Setup', icon: '⚙' },
    { to: '/catalog', label: 'Course Catalog', icon: '▦' },
    { to: '/question-bank', label: 'Question Bank', icon: '?' },
    { to: '/profile', label: 'My Profile', icon: '○' },
  ]
})

const roleLabel = computed(() => ({ STUDENT: 'Student', INSTRUCTOR: 'Instructor', ADMIN: 'Administrator' }[auth.state.user?.role] || 'User'))

function isActive(to) {
  return route.path === to || (to !== '/' && route.path.startsWith(`${to}/`))
}
</script>

<template>
  <div class="app-layout">
    <div v-if="mobileOpen" class="mobile-backdrop" aria-hidden="true" @click="mobileOpen = false"></div>
    <aside class="sidebar" :class="{ 'sidebar-open': mobileOpen }">
      <RouterLink class="brand" :to="items[0]?.to || '/'" @click="mobileOpen = false">
        <div class="brand-mark">E</div>
        <div><strong>EduSphere</strong><span>Learning Management</span></div>
      </RouterLink>

      <div class="role-chip">{{ roleLabel }} Portal</div>
      <nav class="side-nav">
        <RouterLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          :class="{ active: isActive(item.to) }"
          :aria-current="isActive(item.to) ? 'page' : undefined"
          @click="mobileOpen = false"
        >
          <span class="nav-icon">{{ item.icon }}</span><span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <div class="user-mini">
          <div class="avatar">{{ auth.state.user?.username?.slice(0, 1) || 'U' }}</div>
          <div><strong>{{ auth.state.user?.username }}</strong><span>{{ roleLabel }}</span></div>
        </div>
        <button class="btn btn-ghost btn-full" @click="auth.logout()">Sign out</button>
      </div>
    </aside>

    <div class="app-main">
      <header class="topbar">
        <button class="mobile-menu" type="button" aria-label="Open navigation menu" :aria-expanded="mobileOpen" @click="mobileOpen = true">☰</button>
        <div>
          <div class="topbar-eyebrow">EduSphere LMS</div>
          <div class="topbar-title"><slot name="title">Workspace</slot></div>
        </div>
        <div class="topbar-actions"><span v-if="!online" class="offline-chip" title="Network connection is unavailable">Offline</span><slot name="actions" /></div>
      </header>

      <main class="page-content"><slot /></main>
    </div>
  </div>
</template>
