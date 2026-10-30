<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppShell from '../../components/AppShell.vue'
import SectionCard from '../../components/SectionCard.vue'
import DataTable from '../../components/DataTable.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import LoadingState from '../../components/LoadingState.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { api } from '../../services/api.js'
import { auth } from '../../stores/auth.js'
import { toast } from '../../stores/toast.js'
import { QUESTION_TYPES, displayLabel } from '../../utils/format.js'

const questions = ref([])
const detail = ref(null)
const quizzes = ref([])
const error = ref('')
const loading = ref(true)
const pending = reactive({create:false, option:false, attach:false})
const confirmAttach = ref(false)
const role = computed(() => auth.state.user?.role)
const createForm = reactive({ question_text:'', question_type:'MCQ_SINGLE', true_false_correct:'YES' })
const optionForm = reactive({ option_text:'', is_correct:'N', option_order:1, match_side:'L', match_key:'' })
const attachForm = reactive({ quiz_id:'', question_id:'', question_order:1, question_marks:1 })
const numericForm = reactive({ expected_value:'', tolerance:0 })
const keywordForm = reactive({ keyword_order:1, keyword_text:'' })
const questionSearch = ref('')
const questionTypeFilter = ref('ALL')
const filteredQuestions = computed(() => {
  const query = questionSearch.value.trim().toLowerCase()
  return questions.value.filter(q => {
    const matchesText = !query || String(q.question_text || '').toLowerCase().includes(query) || String(q.question_id || '').includes(query)
    const matchesType = questionTypeFilter.value === 'ALL' || q.question_type === questionTypeFilter.value
    return matchesText && matchesType
  })
})
const questionTypeCounts = computed(() => QUESTION_TYPES.reduce((counts, type) => { counts[type] = questions.value.filter(q => q.question_type === type).length; return counts }, {}))

function rows(data){return Array.isArray(data)?data:(data?.results||data?.items||[])}
async function loadQuizChoices() {
  const offeringRows = role.value === 'INSTRUCTOR' ? rows(await api.academics.instructorOfferings()) : rows(await api.academics.offerings(1,200))
  const discovered = []
  const gradingResults = await Promise.allSettled(offeringRows.map(async (o) => ({o, g:await api.academics.grading(o.offering_id)})))
  for (const result of gradingResults) {
    if (result.status !== 'fulfilled') continue
    const {o,g}=result.value
    const comps=(g?.components||[]).filter(c=>c.component_type==='QUIZ')
    const quizResults=await Promise.allSettled(comps.map(async c=>({c, list:rows(await api.quizzes.list(c.component_id))})))
    for(const qr of quizResults){if(qr.status!=='fulfilled')continue;for(const q of qr.value.list)discovered.push({...q,component_name:qr.value.c.component_name,course_code:o.course_code,section_code:o.section_code})}
  }
  quizzes.value=discovered
}
async function load() {
  loading.value=true;error.value=''
  try { const [q] = await Promise.all([api.quizzes.questions(),loadQuizChoices()]); questions.value=rows(q) }
  catch(e){error.value=e.message} finally{loading.value=false}
}
async function showQuestion(id){try{detail.value=await api.quizzes.question(id);attachForm.question_id=id}catch(e){toast.error(e.message)}}
async function createQuestion(){pending.create=true;try{await api.quizzes.createQuestion(createForm);toast.success('Question created.');createForm.question_text='';createForm.true_false_correct='YES';questions.value=rows(await api.quizzes.questions())}catch(e){toast.error(e.message)}finally{pending.create=false}}
async function createOption(){if(!detail.value?.question?.question_id)return;pending.option=true;try{await api.quizzes.createOption({question_id:Number(detail.value.question.question_id),option_text:optionForm.option_text,is_correct:optionForm.is_correct,option_order:Number(optionForm.option_order),match_side:optionForm.match_side,match_key:optionForm.match_key});toast.success('Option created.');await showQuestion(detail.value.question.question_id);optionForm.option_text='';optionForm.option_order++}catch(e){toast.error(e.message)}finally{pending.option=false}}
async function saveNumeric(){try{await api.quizzes.numericRule({question_id:Number(detail.value.question.question_id),expected_value:Number(numericForm.expected_value),tolerance:Number(numericForm.tolerance)});toast.success('Numeric rule saved.');await showQuestion(detail.value.question.question_id)}catch(e){toast.error(e.message)}}
async function addKeyword(){try{await api.quizzes.addKeyword({question_id:Number(detail.value.question.question_id),keyword_order:Number(keywordForm.keyword_order),keyword_text:keywordForm.keyword_text});toast.success('Keyword added.');keywordForm.keyword_text='';keywordForm.keyword_order++;await showQuestion(detail.value.question.question_id)}catch(e){toast.error(e.message)}}
function askAttach(){if(!attachForm.question_id||!attachForm.quiz_id){toast.error('Select a question and quiz first.');return}confirmAttach.value=true}
async function attachQuestion(){confirmAttach.value=false;pending.attach=true;try{await api.quizzes.addQuestion({quiz_id:Number(attachForm.quiz_id),question_id:Number(attachForm.question_id),question_order:Number(attachForm.question_order),question_marks:Number(attachForm.question_marks)});toast.success('Question attached. Earlier graded attempts are unchanged.')}catch(e){toast.error(e.message)}finally{pending.attach=false}}
const selectedQuestion = computed(()=>questions.value.find(q=>String(q.question_id)===String(attachForm.question_id)))
const selectedQuiz = computed(()=>quizzes.value.find(q=>String(q.quiz_id)===String(attachForm.quiz_id)))

onMounted(load)
</script>

<template>
  <AppShell>
    <template #title>Question Bank</template>
    <div class="page-heading"><div><div class="eyebrow">Quiz authoring</div><h1>Reusable question bank</h1><p>Create questions and options, then attach them to a named quiz without typing database IDs.</p></div></div>
    <div v-if="error" class="notice notice-error">{{error}}</div>
    <LoadingState v-else-if="loading" message="Loading question bank and available quizzes…" />
    <template v-else>
      <div class="grid grid-2">
        <SectionCard title="Create question">
          <form class="form-grid" @submit.prevent="createQuestion"><div class="field full"><label>Question text</label><textarea v-model="createForm.question_text" class="textarea" required /></div><div class="field"><label>Question type</label><select v-model="createForm.question_type" class="select"><option v-for="x in QUESTION_TYPES" :key="x" :value="x">{{ displayLabel(x) }}</option></select></div><div v-if="createForm.question_type==='TRUE_FALSE'" class="field"><label>Correct answer</label><select v-model="createForm.true_false_correct" class="select"><option value="YES">Yes</option><option value="NO">No</option></select></div><div v-if="createForm.question_type==='FILL_BLANK'" class="field full"><span class="help">Write the question with visible blank placeholders (for example: “The ___ is the primary key.”), then add one correct answer per blank in the question details.</span></div><div class="field" style="align-self:end"><button class="btn btn-primary" type="submit" :disabled="pending.create">{{pending.create?'Creating…':'Create question'}}</button></div></form>
        </SectionCard>
        <SectionCard title="Attach question to quiz">
          <p class="help" style="margin-bottom:14px">You can append new questions after earlier attempts are submitted and graded. Existing answers remain locked, and earlier results are preserved. Adding is unavailable while any attempt is unfinished.</p>
          <form class="form-grid" @submit.prevent="askAttach">
            <div class="field full"><label>Quiz</label><select v-model="attachForm.quiz_id" class="select" required><option value="" disabled>Select quiz</option><option v-for="q in quizzes" :key="q.quiz_id" :value="q.quiz_id">{{q.course_code}} · {{q.quiz_title}} · Section {{q.section_code}}</option></select></div>
            <div class="field full"><label>Question</label><select v-model="attachForm.question_id" class="select" required><option value="" disabled>Select question</option><option v-for="q in questions" :key="q.question_id" :value="q.question_id">{{q.question_text}}</option></select></div>
            <div class="field"><label>Question order</label><input v-model="attachForm.question_order" type="number" min="1" class="input" required /></div><div class="field"><label>Marks</label><input v-model="attachForm.question_marks" type="number" min="0.1" step="0.1" class="input" required /></div>
            <div class="field full"><button class="btn btn-primary" type="submit" :disabled="pending.attach||!quizzes.length">{{pending.attach?'Attaching…':'Attach to quiz'}}</button></div>
          </form>
        </SectionCard>
      </div>
      <SectionCard title="Question bank" subtitle="Search reusable questions, filter by type, and open a question to manage its answer settings.">
        <div class="question-bank-tools">
          <div class="field question-search-field"><label for="question-bank-search">Search questions</label><input id="question-bank-search" v-model="questionSearch" class="input" placeholder="Search question text or ID…" /></div>
          <div class="field question-filter-field"><label for="question-type-filter">Question type</label><select id="question-type-filter" v-model="questionTypeFilter" class="select"><option value="ALL">All types ({{ questions.length }})</option><option v-for="type in QUESTION_TYPES" :key="type" :value="type">{{ displayLabel(type) }} ({{ questionTypeCounts[type] || 0 }})</option></select></div>
          <div class="question-bank-count"><strong>{{ filteredQuestions.length }}</strong><span>of {{ questions.length }} questions</span></div>
        </div>
        <DataTable :rows="filteredQuestions" :columns="[{key:'question_text',label:'Question'},{key:'question_type',label:'Type'}]" :searchable="false" empty="No questions match these filters."><template #cell-question_type="{value}"><StatusBadge :value="value" /></template><template #actions="{row}"><button class="btn btn-soft btn-sm" :class="{ 'btn-secondary': detail?.question?.question_id === row.question_id }" @click="showQuestion(row.question_id)">{{ detail?.question?.question_id === row.question_id ? 'Selected' : 'Open details' }}</button></template></DataTable>
      </SectionCard>
      <SectionCard v-if="detail" title="Question details" subtitle="Correct-answer metadata is visible only in authoring views."><div class="notice notice-info" style="margin-bottom:16px"><strong>{{detail.question?.question_text}}</strong><br/>Question type: {{ displayLabel(detail.question?.question_type) }}</div><DataTable v-if="detail.options?.length" :rows="detail.options||[]" :columns="[{key:'option_order',label:'Order'},{key:'option_text',label:'Option'},{key:'is_correct',label:'Correct'}]"><template #cell-is_correct="{value}"><StatusBadge :value="value" /></template></DataTable><form v-if="detail.question?.question_type!=='FILL_BLANK'" class="form-grid form-grid-3" style="margin-top:18px" @submit.prevent="createOption"><div class="field"><label>Option text</label><input v-model="optionForm.option_text" class="input" required /></div><div class="field"><label>Correct?</label><select v-model="optionForm.is_correct" class="select"><option value="Y">Yes</option><option value="N">No</option></select></div><div class="field"><label>Order</label><input v-model="optionForm.option_order" type="number" min="1" class="input" required /></div><template v-if="detail.question?.question_type==='MATCHING'"><div class="field"><label>Side</label><select v-model="optionForm.match_side" class="select"><option value="L">Left</option><option value="R">Right</option></select></div><div class="field"><label>Match key</label><input v-model="optionForm.match_key" class="input" placeholder="A, B, C…" /></div></template><div class="field full"><button class="btn btn-primary" type="submit" :disabled="pending.option">{{pending.option?'Adding…':'Add option'}}</button></div></form></SectionCard>
      <div v-if="detail?.question?.question_type==='NUMERICAL'" class="grid grid-2" style="margin-top:18px"><SectionCard title="Numerical grading rule"><form class="form-grid" @submit.prevent="saveNumeric"><div class="field"><label>Expected value</label><input v-model="numericForm.expected_value" type="number" step="any" class="input" required/></div><div class="field"><label>Tolerance</label><input v-model="numericForm.tolerance" type="number" step="any" min="0" class="input" required/><span class="help">Accepted when absolute error is within tolerance.</span></div><button class="btn btn-primary" type="submit">Save rule</button></form></SectionCard><SectionCard title="Current rule"><div class="metric-list"><div class="metric-pair"><span>Expected</span><strong>{{detail.numeric_rule?.expected_value ?? '—'}}</strong></div><div class="metric-pair"><span>Tolerance</span><strong>{{detail.numeric_rule?.tolerance ?? '—'}}</strong></div></div></SectionCard></div>
      <SectionCard v-if="['SHORT_TEXT','FILL_BLANK'].includes(detail?.question?.question_type)" :title="detail?.question?.question_type==='FILL_BLANK' ? 'Blank answers' : 'Accepted keywords'" style="margin-top:18px"><div v-if="detail?.question?.question_type==='FILL_BLANK'" class="notice notice-info" style="margin-bottom:14px">Add exactly one correct answer for each blank, in left-to-right order. Use 1, 2, 3, … for the blank positions.</div><div v-else class="notice notice-info" style="margin-bottom:14px">Add accepted answers. Student answers are matched case-insensitively after trimming whitespace.</div><form class="form-grid form-grid-3" @submit.prevent="addKeyword"><div class="field"><label>Order</label><input v-model="keywordForm.keyword_order" type="number" min="1" class="input" required/></div><div class="field"><label>{{detail?.question?.question_type==='FILL_BLANK' ? 'Correct answer' : 'Accepted keyword'}}</label><input v-model="keywordForm.keyword_text" class="input" required/></div><div class="field" style="align-self:end"><button class="btn btn-primary" type="submit">{{detail?.question?.question_type==='FILL_BLANK' ? 'Add blank answer' : 'Add keyword'}}</button></div></form><DataTable :rows="detail.keywords||[]" :columns="[{key:'keyword_order',label:'Order'},{key:'keyword_text',label:detail?.question?.question_type==='FILL_BLANK' ? 'Correct answer' : 'Accepted keyword'}]" /></SectionCard>
    </template>
    <ConfirmDialog :open="confirmAttach" title="Attach question?" :message="`Append “${selectedQuestion?.question_text||'selected question'}” to “${selectedQuiz?.quiz_title||'selected quiz'}”? Existing graded attempts stay unchanged; future attempts include the new question.`" confirm-label="Attach" :busy="pending.attach" @cancel="confirmAttach=false" @confirm="attachQuestion" />
  </AppShell>
</template>
