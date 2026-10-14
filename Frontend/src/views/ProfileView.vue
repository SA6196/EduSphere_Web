<script setup>
import { onMounted, ref } from 'vue'
import AppShell from '../components/AppShell.vue'
import SectionCard from '../components/SectionCard.vue'
import StatusBadge from '../components/StatusBadge.vue'
import LoadingState from '../components/LoadingState.vue'
import { api } from '../services/api.js'
import { formatDateTime, titleCase } from '../utils/format.js'

const user = ref(null)
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try { user.value = await api.auth.me() } catch (e) { error.value = e.message } finally { loading.value = false }
})
</script>

<template>
  <AppShell>
    <template #title>My Profile</template>
    <div class="page-heading">
      <div><div class="eyebrow">Account</div><h1>Profile & access</h1><p>Your authenticated EduSphere identity and role information.</p></div>
    </div>
    <div v-if="error" class="notice notice-error">{{ error }}</div>
    <LoadingState v-else-if="loading" message="Loading your profile…" />
    <SectionCard v-else-if="user" title="Account details" subtitle="Your account identity and access status.">
      <div class="grid grid-2">
        <div class="field"><label>Username</label><div>{{ user.username }}</div></div>
        <div class="field"><label>Role</label><div><StatusBadge :value="user.role" /></div></div>
        <div class="field"><label>Account status</label><div><StatusBadge :value="user.account_status" /></div></div>
        <div class="field"><label>Email</label><div>{{ user.email || '—' }}</div></div>
        <div class="field"><label>Phone</label><div>{{ user.phone || '—' }}</div></div>
        <div class="field"><label>Last login</label><div>{{ formatDateTime(user.last_login) }}</div></div>
      </div>
      <div class="notice notice-info" style="margin-top:18px">Your portal permissions are determined by the <strong>{{ titleCase(user.role) }}</strong> role and are enforced again by the Django and Oracle authorization layers.</div>
    </SectionCard>
  </AppShell>
</template>
