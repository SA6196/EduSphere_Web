<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth } from '../stores/auth.js'
import { roleHome } from '../utils/roles.js'

const username = ref('')
const password = ref('')
const error = ref('')
const route = useRoute()
const router = useRouter()

async function submit() {
  error.value = ''
  try {
    const user = await auth.login(username.value.trim(), password.value)
    const requested = route.query.redirect
    await router.replace(typeof requested === 'string' && requested !== '/login' ? requested : roleHome(user.role))
  } catch (e) {
    error.value = e.message || 'Login failed.'
  }
}
</script>

<template>
  <div class="login-page">
    <section class="login-hero">
      <div class="login-brand"><span class="login-brand-mark">E</span> EduSphere LMS</div>
      <div class="login-copy">
        <div class="eyebrow">B.Tech Learning Management System</div>
        <h1>Learning, teaching and progress in one place.</h1>
        <p>Role-aware access for students, instructors and administrators, backed by the hardened EduSphere Django API and normalized Oracle database.</p>
        <div class="login-points">
          <div class="login-point"><strong>Student</strong><span>Courses, assignments, quizzes, attendance, marks and GPA.</span></div>
          <div class="login-point"><strong>Instructor</strong><span>Teaching workspace, roster, assessments and grading.</span></div>
          <div class="login-point"><strong>Admin</strong><span>Operational overview, reporting and academic controls.</span></div>
        </div>
      </div>
      <small style="color:#9fb0df">EduSphere · Django REST + Oracle</small>
    </section>

    <section class="login-form-side">
      <form class="login-form" @submit.prevent="submit">
        <div class="eyebrow">Secure sign in</div>
        <h2>Welcome back</h2>
        <p>Use your EduSphere account. The portal automatically opens the correct workspace for your role.</p>

        <div v-if="error" class="notice notice-error" style="margin-bottom:14px">{{ error }}</div>

        <div class="field">
          <label for="username">Username</label>
          <input id="username" v-model="username" class="input" autocomplete="username" placeholder="e.g. FINAL_S7" required />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input id="password" v-model="password" class="input" type="password" autocomplete="current-password" placeholder="Your password" required />
        </div>

        <button class="btn btn-primary btn-full" type="submit" :disabled="auth.state.loading">
          {{ auth.state.loading ? 'Signing in…' : 'Sign in to EduSphere' }}
        </button>

        <div style="margin-top:12px;text-align:center"><RouterLink to="/signup">Request a student account</RouterLink></div>
        <div class="login-demo">
          Your session is protected by role-based access controls. Backend and database connection details are managed separately from the user interface.
        </div>
      </form>
    </section>
  </div>
</template>
