<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../../components/AppShell.vue'
import SectionCard from '../../components/SectionCard.vue'
import DataTable from '../../components/DataTable.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import LoadingState from '../../components/LoadingState.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'

const route=useRoute(), router=useRouter()
const quizId=computed(()=>Number(route.params.quizId))
const rows=ref([]), detail=ref(null), loading=ref(true), error=ref('')
const form=reactive({final_marks:'',notes:''})
const busy=ref(false), releaseBusy=ref(false), retryBusy=ref(false)
const hasLongText = computed(() => (detail.value?.question_grades || []).some(q => q.question_type === 'LONG_TEXT'))
const manualAnswers = reactive({})
const computedMarks = computed(() => (detail.value?.question_grades || []).reduce((total, q) => total + (
  q.question_type === 'LONG_TEXT'
    ? Number(manualAnswers[q.question_id]?.marks_awarded || 0)
    : Number(q.marks_awarded || 0)
), 0))

async function load(){
  loading.value=true; error.value=''
  try { rows.value=await api.quizzes.grading(quizId.value) } catch(e){error.value=e.message} finally{loading.value=false}
}
async function open(row){
  try {
    detail.value=await api.quizzes.gradingDetail(row.attempt_id)
    form.final_marks=detail.value.grading.final_marks
    form.notes=detail.value.grading.instructor_notes||''
    for (const q of detail.value.question_grades || []) {
      if (q.question_type === 'LONG_TEXT') manualAnswers[q.question_id] = {
        marks_awarded: Number(q.marks_awarded || 0),
        feedback: q.grading_note?.startsWith('Manual') ? q.grading_note : '',
      }
    }
  } catch(e){toast.error(e.message)}
}
async function retry(row){
  retryBusy.value=true
  try{
    const result=await api.quizzes.retryAutoGrading(Number(row.attempt_id))
    toast.success(`Auto-grading completed: ${result.auto_marks} / ${result.max_marks}.` )
    await load()
    const updated=rows.value.find(x=>Number(x.attempt_id)===Number(row.attempt_id))
    if(updated) await open(updated)
  }catch(e){toast.error(e.message)}finally{retryBusy.value=false}
}
async function review(){
  if(!detail.value)return
  busy.value=true
  try{
    const question_reviews=(detail.value.question_grades||[])
      .filter(q=>q.question_type==='LONG_TEXT')
      .map(q=>({question_id:q.question_id,marks_awarded:Number(manualAnswers[q.question_id]?.marks_awarded),feedback:manualAnswers[q.question_id]?.feedback}))
    await api.quizzes.reviewGrading(detail.value.grading.attempt_id,{final_marks:computedMarks.value,notes:form.notes,question_reviews})
    toast.success('Grade reviewed and stored in STUDENT_MARK.')
    await load(); await open(rows.value.find(x=>Number(x.attempt_id)===Number(detail.value.grading.attempt_id)))
  }catch(e){toast.error(e.message)}finally{busy.value=false}
}
async function release(){
  if(!detail.value)return
  releaseBusy.value=true
  try{await api.quizzes.releaseGrading(detail.value.grading.attempt_id);toast.success('Marks released. Student visibility still follows the quiz mark-view switch.');await load();await open(rows.value.find(x=>Number(x.attempt_id)===Number(detail.value.grading.attempt_id)))}catch(e){toast.error(e.message)}finally{releaseBusy.value=false}
}
onMounted(load)
</script>

<template>
<AppShell>
  <template #title>Quiz Grading Review</template>
  <div class="page-heading"><div><div class="eyebrow">Instructor control</div><h1>Automatic grading review</h1><p>Review calculated marks, optionally adjust the final mark, then release the result. Student visibility remains controlled separately.</p></div><button class="btn btn-soft" @click="router.back()">Back</button></div>
  <div v-if="error" class="notice notice-error">{{error}}</div>
  <LoadingState v-else-if="loading" message="Loading automatic grading…" />
  <template v-else>
    <SectionCard title="Submitted attempts">
      <div class="notice notice-info" style="margin-bottom:14px">Submitted attempts that have no grading record are shown as <strong>NOT_GRADED</strong>. Use <strong>Auto-grade</strong> to calculate and store the mark without asking the student to resubmit.</div>
      <DataTable :rows="rows" :columns="[{key:'student_name',label:'Student'},{key:'admission_no',label:'Admission'},{key:'attempt_no',label:'Attempt'},{key:'auto_marks',label:'Auto marks'},{key:'final_marks',label:'Final marks'},{key:'max_marks',label:'Maximum'},{key:'grading_status',label:'Status'},{key:'submitted_at',label:'Submitted'}]">
        <template #cell-grading_status="{value}"><StatusBadge :value="value"/></template>
        <template #actions="{row}"><div style="display:flex;gap:8px;flex-wrap:wrap"><button v-if="row.grading_status==='NOT_GRADED'" class="btn btn-primary btn-sm" :disabled="retryBusy" @click="retry(row)">{{retryBusy?'Grading…':'Auto-grade'}}</button><button v-if="row.grading_status!=='NOT_GRADED'" class="btn btn-soft btn-sm" @click="open(row)">Review</button></div></template>
      </DataTable>
    </SectionCard>

    <SectionCard v-if="detail" title="Selected attempt review" subtitle="Review the automatic score and question-level notes. Long-text answers require instructor judgement.">
      <div v-if="hasLongText" class="notice notice-warning" style="margin-bottom:14px"><strong>Manual review needed:</strong> this attempt contains a long-text response. Review the written response and set the final mark before releasing results.</div>
      <div class="grid grid-2">
        <div class="notice notice-info">Auto: <strong>{{detail.grading.auto_marks}}</strong> / {{detail.grading.max_marks}}</div>
        <div class="notice notice-info">Status: <strong>{{detail.grading.grading_status}}</strong></div>
      </div>
      <DataTable :rows="detail.question_grades" :columns="[{key:'question_order',label:'#'},{key:'question_type',label:'Type'},{key:'marks_awarded',label:'Auto marks'},{key:'max_marks',label:'Maximum'},{key:'grading_note',label:'Feedback'}]" />
      <div v-for="q in detail.question_grades.filter(q=>q.question_type==='LONG_TEXT')" :key="q.question_id" class="card" style="margin-top:14px;padding:16px">
        <strong>Question {{q.question_order}}: {{q.question_text}}</strong>
        <div class="field" style="margin-top:10px"><label>Student's submitted answer</label><p class="notice notice-info" style="white-space:pre-wrap">{{q.response_text || '(No answer submitted)'}}</p></div>
        <div class="field"><label>Manual marks (max {{q.max_marks}})</label><input v-model.number="manualAnswers[q.question_id].marks_awarded" type="number" min="0" :max="q.max_marks" step="0.01" class="input" required /></div>
        <div class="field"><label>Rubric criteria / inline feedback</label><textarea v-model="manualAnswers[q.question_id].feedback" class="textarea" maxlength="1000" placeholder="State the criteria met, missing points and feedback" required /></div>
      </div>
      <form class="form-grid" style="margin-top:18px" @submit.prevent="review">
        <div class="field"><label>Final marks</label><input :value="computedMarks.toFixed(2)" type="number" min="0" :max="detail.grading.max_marks" step="0.01" class="input" readonly/></div>
        <div class="field full"><label>Instructor notes</label><textarea v-model="form.notes" class="textarea"/></div>
        <div class="field full" style="display:flex;gap:8px"><button class="btn btn-primary" :disabled="busy||detail.grading.grading_status==='RELEASED'" type="submit">{{busy?'Saving…':'Review / finalize mark'}}</button><button class="btn btn-success" :disabled="releaseBusy||detail.grading.grading_status!=='REVIEWED'" type="button" @click="release">{{releaseBusy?'Releasing…':'Release marks'}}</button></div>
      </form>
    </SectionCard>
  </template>
</AppShell>
</template>
