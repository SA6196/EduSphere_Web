<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../../components/AppShell.vue'
import SectionCard from '../../components/SectionCard.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import LoadingState from '../../components/LoadingState.vue'
import EmptyState from '../../components/EmptyState.vue'
import { api } from '../../services/api.js'
import { displayLabel, compactNumber } from '../../utils/format.js'

const router = useRouter()
const attempts = ref([])
const selectedAttempt = ref(null)
const review = ref(null)
const loading = ref(true)
const reviewLoading = ref(false)
const error = ref('')
const reviewError = ref('')

const selectedTitle = computed(() => selectedAttempt.value?.quiz_title || 'Quiz attempt')

function formatDate(value) {
  if (!value) return '—'
  try { return new Date(value).toLocaleString() } catch { return String(value) }
}
function responseText(q) {
  if (q.question_type === 'FILL_BLANK') {
    try {
      const values = JSON.parse(q.response_text || '[]')
      return Array.isArray(values) ? values.map((x, i) => `Blank ${i + 1}: ${x || '—'}`).join(' · ') : String(q.response_text || '—')
    } catch { return String(q.response_text || '—') }
  }
  if (q.question_type === 'MATCHING') {
    return q.response_matches?.length
      ? q.response_matches.map(x => `${x.left_option_text} → ${x.right_option_text}`).join(' · ')
      : 'No matching pairs submitted.'
  }
  if (q.question_type === 'ORDERING') {
    return q.response_order?.length
      ? q.response_order.map(x => `${x.position_order}. ${x.option_text}`).join(' · ')
      : 'No ordering submitted.'
  }
  if (q.options?.length) {
    const selected = q.options.filter(o => o.is_selected).map(o => o.option_text)
    if (selected.length) return selected.join(' · ')
  }
  return q.response_text || 'No response.'
}

async function openAttempt(attempt) {
  selectedAttempt.value = attempt
  review.value = null
  reviewError.value = ''
  if (!attempt.answer_review_visible) return
  reviewLoading.value = true
  try {
    review.value = await api.quizzes.review(attempt.attempt_id)
  } catch (e) { reviewError.value = e.message } finally { reviewLoading.value = false }
}

onMounted(async () => {
  try {
    const data = await api.quizzes.attempts()
    attempts.value = data?.attempts || []
  } catch (e) { error.value = e.message } finally { loading.value = false }
})
</script>

<template>
  <AppShell>
    <template #title>My Quiz Attempts</template>
    <div class="page-heading">
      <div><div class="eyebrow">Quiz history</div><h1>My attempts & answers</h1><p>Open a submitted attempt to see your response, marks when released for viewing, and correct answers when answer review is enabled.</p></div>
      <button class="btn btn-soft" @click="router.push('/student/performance')">Back to performance</button>
    </div>

    <div v-if="error" class="notice notice-error">{{ error }}</div>
    <LoadingState v-else-if="loading" message="Loading quiz attempts…" />
    <template v-else>
      <SectionCard title="Submitted quiz attempts" subtitle="The instructor's current visibility settings control what marks and answers are shown.">
        <EmptyState v-if="!attempts.length" title="No submitted quiz attempts" message="Your submitted quiz attempts will appear here." />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead><tr><th>Course</th><th>Quiz</th><th>Attempt</th><th>Submitted</th><th>Marks</th><th>Status</th><th></th></tr></thead>
            <tbody>
              <tr v-for="attempt in attempts" :key="attempt.attempt_id">
                <td><strong>{{ attempt.course_code }}</strong><div class="course-meta">{{ attempt.course_name }}</div></td>
                <td>{{ attempt.quiz_title }}</td>
                <td>#{{ attempt.attempt_no }}</td>
                <td>{{ formatDate(attempt.submitted_at) }}</td>
                <td>{{ attempt.marks_visible ? `${compactNumber(attempt.marks_obtained)} / ${compactNumber(attempt.max_marks)}` : 'Hidden' }}</td>
                <td><StatusBadge :value="attempt.marks_visible ? 'MARKS_VISIBLE' : (attempt.grading_status || 'SUBMITTED')" /></td>
                <td><button class="btn btn-primary btn-sm" @click="openAttempt(attempt)">{{ attempt.answer_review_visible ? 'View attempt' : 'View result' }}</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard v-if="selectedAttempt" :title="`${selectedTitle} · Attempt #${selectedAttempt.attempt_no}`" subtitle="Your submitted responses are shown below. Correct answers appear only when answer review is enabled.">
        <div class="stats-grid" style="margin-bottom:18px">
          <div class="stat-card"><div><div class="stat-label">Submitted</div><div class="stat-value" style="font-size:18px">{{ formatDate(selectedAttempt.submitted_at) }}</div></div></div>
          <div class="stat-card"><div><div class="stat-label">Marks</div><div class="stat-value">{{ selectedAttempt.marks_visible ? `${compactNumber(selectedAttempt.marks_obtained)} / ${compactNumber(selectedAttempt.max_marks)}` : 'Hidden' }}</div></div></div>
          <div class="stat-card"><div><div class="stat-label">Answer review</div><div class="stat-value" style="font-size:18px">{{ selectedAttempt.answer_review_visible ? 'Enabled' : 'Hidden' }}</div></div></div>
        </div>

        <div v-if="reviewError" class="notice notice-error">{{ reviewError }}</div>
        <LoadingState v-else-if="reviewLoading" message="Loading your submitted answers…" />
        <div v-else-if="review?.questions?.length" class="quiz-review-list">
          <article v-for="q in review.questions" :key="q.question_id" class="quiz-question">
            <div class="quiz-question-head">
              <div class="question-number">{{ q.question_order }}</div>
              <div><strong>{{ q.question_text }}</strong><div class="course-meta">{{ q.question_marks }} mark(s) · {{ displayLabel(q.question_type) }}</div></div>
              <StatusBadge :value="q.is_correct || 'REVIEWED'" style="margin-left:auto" />
              <strong v-if="selectedAttempt.marks_visible" style="margin-left:8px">{{ q.marks_awarded ?? '—' }} / {{ q.question_marks }}</strong>
            </div>

            <div class="notice notice-info" style="margin-top:12px"><strong>Your answer:</strong> {{ responseText(q) }}</div>

            <template v-if="q.correct_answer">
              <div v-if="q.correct_answer.type==='options'" class="option-list" style="margin-top:10px">
                <div class="option-row" v-for="o in q.correct_answer.options" :key="o.option_id"><strong>Correct</strong><span>{{ o.option_text }}</span></div>
              </div>
              <div v-else-if="q.correct_answer.type==='ordering'" class="notice notice-success" style="margin-top:10px"><strong>Correct order:</strong> {{ q.correct_answer.options.map(o => `${o.position}. ${o.option_text}`).join(' · ') }}</div>
              <div v-else-if="q.correct_answer.type==='matching'" class="option-list" style="margin-top:10px">
                <div class="option-row" v-for="pair in q.correct_answer.pairs" :key="`${pair.left_option_id}-${pair.right_option_id}`"><strong>Correct</strong><span>{{ pair.left_option_text }} → {{ pair.right_option_text }}</span></div>
              </div>
              <div v-else-if="q.correct_answer.type==='numerical'" class="notice notice-success" style="margin-top:10px"><strong>Correct numerical answer:</strong> {{ q.correct_answer.expected_value }}<span v-if="q.correct_answer.tolerance !== null && q.correct_answer.tolerance !== undefined"> ± {{ q.correct_answer.tolerance }}</span></div>
              <div v-else-if="q.correct_answer.type==='text'" class="notice notice-success" style="margin-top:10px"><strong>Accepted answer{{ q.correct_answer.keywords.length === 1 ? '' : 's' }}:</strong> {{ q.correct_answer.keywords.map(k => k.text).join(' · ') }}</div>
            </template>
            <div v-if="q.grading_note" class="course-meta" style="margin-top:9px">{{ q.grading_note }}</div>
          </article>
        </div>
        <div v-else-if="!selectedAttempt.answer_review_visible" class="notice notice-info">Answer review is currently hidden by the instructor. You can still see the result above when marks are visible.</div>
        <div v-else class="notice notice-info">No detailed answer review is available for this attempt.</div>
      </SectionCard>
    </template>
  </AppShell>
</template>
