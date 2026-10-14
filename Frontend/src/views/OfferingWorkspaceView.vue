<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from '../components/AppShell.vue'
import StatusBadge from '../components/StatusBadge.vue'
import EmptyState from '../components/EmptyState.vue'
import LoadingState from '../components/LoadingState.vue'
import WorkspaceOverviewTab from '../components/workspace/WorkspaceOverviewTab.vue'
import WorkspaceMaterialsTab from '../components/workspace/WorkspaceMaterialsTab.vue'
import WorkspaceAnnouncementsTab from '../components/workspace/WorkspaceAnnouncementsTab.vue'
import WorkspaceSessionsTab from '../components/workspace/WorkspaceSessionsTab.vue'
import WorkspaceAssignmentsTab from '../components/workspace/WorkspaceAssignmentsTab.vue'
import WorkspaceQuizzesTab from '../components/workspace/WorkspaceQuizzesTab.vue'
import WorkspaceExamsTab from '../components/workspace/WorkspaceExamsTab.vue'
import WorkspaceAttendanceTab from '../components/workspace/WorkspaceAttendanceTab.vue'
import WorkspaceRosterGradingTab from '../components/workspace/WorkspaceRosterGradingTab.vue'
import WorkspaceSchemeEditorTab from '../components/workspace/WorkspaceSchemeEditorTab.vue'
import WorkspaceRecordAttendanceTab from '../components/workspace/WorkspaceRecordAttendanceTab.vue'
import { api } from '../services/api.js'
import { displayLabel } from '../utils/format.js'
import { auth } from '../stores/auth.js'

const route = useRoute()
const offeringId = computed(() => Number(route.params.offeringId))
const role = computed(() => auth.state.user?.role)
const isStudent = computed(() => role.value === 'STUDENT')
const isInstructor = computed(() => role.value === 'INSTRUCTOR')
const isAdmin = computed(() => role.value === 'ADMIN')

const offering = ref(null)
const grading = ref(null)
const materials = ref([])
const announcements = ref([])
const sessions = ref([])
const exams = ref([])
const assignments = ref([])
const quizzes = ref([])
const roster = ref([])
const attendance = ref([])
const accessLimited = ref(false)
const error = ref('')
const loading = ref(true)
const activeTab = ref('overview')

const tabs = computed(() => {
  const list = [
    ['overview','Overview'], ['materials','Materials'], ['announcements','Announcements'],
    ['sessions','Sessions'], ['assignments','Assignments'], ['quizzes','Quizzes'], ['exams','Exams'],
  ]
  if (isStudent.value) list.push(['attendance','My Attendance'])
  if (isInstructor.value || isAdmin.value) list.push(['roster','Roster & Grading'], ['scheme','Grading Scheme'], ['record-attendance','Record Attendance'])
  return list
})
const components = computed(() => grading.value?.components || [])
function unconfigured(c, childKey) {
  const child = c?.[childKey]
  if (child !== null && child !== undefined && child !== '') return false
  return String(c?.configured || 'N').toUpperCase() !== 'Y'
}
const assignmentComponents = computed(() => components.value.filter((c) => c.component_type === 'ASSIGNMENT' && unconfigured(c, 'assignment_id')))
const quizComponents = computed(() => components.value.filter((c) => c.component_type === 'QUIZ' && unconfigured(c, 'quiz_id')))
const examComponents = computed(() => components.value.filter((c) => c.component_type === 'EXAM' && unconfigured(c, 'exam_id')))
const offeringStatus = computed(() => String(offering.value?.offering_status || '').toUpperCase())
const creationAllowed = computed(() => ['PLANNED','OPEN'].includes(offeringStatus.value))
const studentSubmissionAllowed = computed(() => offeringStatus.value === 'OPEN')
const displayClassStatus = computed(() => displayLabel(offeringStatus.value))
const lifecycleBlockedMessage = computed(() => creationAllowed.value ? '' : `New teaching content cannot be created while this class is ${displayClassStatus.value || 'not active'}. Existing content and grading remain available.`)
const submissionBlockedMessage = computed(() => studentSubmissionAllowed.value ? '' : `New assignment submissions are unavailable because this class is ${displayClassStatus.value || 'not open'}. Existing submissions and results remain visible.`)
function rows(data) { return Array.isArray(data) ? data : (data?.results || data?.items || []) }

async function load() {
  loading.value = true; error.value = ''; accessLimited.value = false
  try {
    offering.value = await api.academics.offering(offeringId.value)
    try { grading.value = await api.academics.grading(offeringId.value) }
    catch (e) {
      if (e.status === 403 && isStudent.value) { accessLimited.value = true; return }
      throw e
    }

    const common = await Promise.all([
      api.materials.list(offeringId.value), api.announcements.list(offeringId.value),
      api.attendance.sessions(offeringId.value), api.exams.list(offeringId.value),
    ])
    materials.value = rows(common[0]); announcements.value = rows(common[1]); sessions.value = rows(common[2]); exams.value = rows(common[3])

    assignments.value = (await Promise.all(components.value.filter(c=>c.component_type==='ASSIGNMENT').map(async (c) => rows(await api.assignments.list(c.component_id)).map((x) => ({...x, component_id:c.component_id, component_name:c.component_name}))))).flat()
    quizzes.value = (await Promise.all(components.value.filter(c=>c.component_type==='QUIZ').map(async (c) => rows(await api.quizzes.list(c.component_id)).map((x) => ({...x, component_name:c.component_name}))))).flat()

    if (isStudent.value) attendance.value = rows(await api.attendance.myOffering(offeringId.value))
    if (isInstructor.value || isAdmin.value) {
      const r = await api.academics.roster(offeringId.value)
      roster.value = r?.students || []
    }
  } catch (e) { error.value = e.message } finally { loading.value = false }
}

onMounted(load)
watch(offeringId, () => { activeTab.value='overview'; load() })
</script>

<template>
  <AppShell>
    <template #title>{{ offering?.course_code || 'Class' }} Workspace</template>
    <div class="page-heading">
      <div><div class="eyebrow">Class workspace</div><h1>{{ offering?.course_name || 'Class workspace' }}</h1><p v-if="offering">{{ offering.course_code }} · Section {{ offering.section_code }}</p></div>
      <StatusBadge v-if="offering" :value="offering.offering_status" />
    </div>

    <div v-if="error" class="notice notice-error">{{ error }}</div>
    <LoadingState v-else-if="loading" message="Loading class workspace…" />
    <div v-else-if="accessLimited" class="section-card">
      <EmptyState title="Enrollment required" message="You can view the catalog entry, but class workspace data is available only after enrollment."><RouterLink class="btn btn-primary" to="/catalog">Back to catalog</RouterLink></EmptyState>
    </div>
    <template v-else-if="grading && offering">
      <div class="tabs"><button v-for="tab in tabs" :key="tab[0]" class="tab" :class="{active:activeTab===tab[0]}" @click="activeTab=tab[0]">{{ tab[1] }}</button></div>

      <WorkspaceOverviewTab v-if="activeTab==='overview'" :offering="offering" :grading="grading" :components="components" />
      <WorkspaceMaterialsTab v-else-if="activeTab==='materials'" :offering-id="offeringId" :materials="materials" :can-create="isInstructor&&creationAllowed" :blocked-message="isInstructor?lifecycleBlockedMessage:''" @refresh="load" />
      <WorkspaceAnnouncementsTab v-else-if="activeTab==='announcements'" :offering-id="offeringId" :announcements="announcements" :can-create="(isInstructor||isAdmin)&&creationAllowed" :blocked-message="(isInstructor||isAdmin)?lifecycleBlockedMessage:''" @refresh="load" />
      <WorkspaceSessionsTab v-else-if="activeTab==='sessions'" :offering-id="offeringId" :sessions="sessions" :can-create="(isInstructor||isAdmin)&&creationAllowed" :blocked-message="(isInstructor||isAdmin)?lifecycleBlockedMessage:''" @refresh="load" />
      <WorkspaceAssignmentsTab v-else-if="activeTab==='assignments'" :assignments="assignments" :assignment-components="assignmentComponents" :roster="roster" :is-instructor="isInstructor" :is-student="isStudent" :can-create="creationAllowed" :can-submit="studentSubmissionAllowed" :create-blocked-message="lifecycleBlockedMessage" :submit-blocked-message="submissionBlockedMessage" @refresh="load" />
      <WorkspaceQuizzesTab v-else-if="activeTab==='quizzes'" :quizzes="quizzes" :quiz-components="quizComponents" :is-instructor="isInstructor" :is-student="isStudent" :can-create="creationAllowed" :create-blocked-message="lifecycleBlockedMessage" @refresh="load" />
      <WorkspaceExamsTab v-else-if="activeTab==='exams'" :exams="exams" :exam-components="examComponents" :can-create="(isInstructor||isAdmin)&&creationAllowed" :blocked-message="(isInstructor||isAdmin)?lifecycleBlockedMessage:''" @refresh="load" />
      <WorkspaceAttendanceTab v-else-if="activeTab==='attendance'" :attendance="attendance" />
      <WorkspaceSchemeEditorTab v-else-if="activeTab==='scheme'" :offering-id="offeringId" @refresh="load" />
      <WorkspaceRosterGradingTab v-else-if="activeTab==='roster'" :components="components" :roster="roster" :assignments="assignments" @refresh="load" />
      <WorkspaceRecordAttendanceTab v-else-if="activeTab==='record-attendance'" :sessions="sessions" :roster="roster" :can-record="creationAllowed" :blocked-message="lifecycleBlockedMessage" @refresh="load" />
    </template>
  </AppShell>
</template>
