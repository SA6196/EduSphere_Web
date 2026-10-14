<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../../components/AppShell.vue'
import SectionCard from '../../components/SectionCard.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import LoadingState from '../../components/LoadingState.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import ErrorState from '../../components/ErrorState.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
import { errorPresentation, isQuizAttemptRequired } from '../../utils/errors.js'
import { displayLabel } from '../../utils/format.js'

const route=useRoute(), router=useRouter()
const quizId=computed(()=>Number(route.params.quizId))
const content=ref(null), attemptId=ref(null), submitted=ref(false), result=ref(null), review=ref(null), loading=ref(true), error=ref(null)
const answers=reactive({}), transmitted=reactive({})
const submitting=ref(false), confirmSubmit=ref(false), remaining=ref(0)
let timer=null, autosaveTimer=null
let saveQueue=Promise.resolve()
const lastSaved=reactive({})
const saveError=ref('')

const questions=computed(()=>content.value?.questions||[])
function answered(q){const v=answers[q.question_id];if(q.question_type==='FILL_BLANK')return Array.isArray(v)&&v.length>0&&v.every(x=>String(x??'').trim().length>0);return Array.isArray(v)?v.length>0:String(v??'').trim().length>0}
const answeredCount=computed(()=>questions.value.filter(answered).length)
const unansweredCount=computed(()=>Math.max(0,questions.value.length-answeredCount.value))
const progressPercent=computed(()=>questions.value.length?Math.round((answeredCount.value/questions.value.length)*100):0)
const draftKey=computed(()=>attemptId.value?`edusphere_quiz_draft_${attemptId.value}`:'')
const timerKey=computed(()=>attemptId.value?`edusphere_quiz_started_${attemptId.value}`:'')
const timeLabel=computed(()=>{const s=Math.max(0,remaining.value);return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`})
const timerTone=computed(()=>remaining.value<=60?'danger':remaining.value<=300?'warning':'normal')

function initializeAnswers(){
  for(const q of questions.value) {
    if(q.question_id in answers) continue
    if(q.question_type==='MCQ_MULTI') answers[q.question_id]=[]
    // ORDERING options arrive in an attempt-specific shuffled order and use
    // opaque handles, never the actual Oracle option IDs or answer order.
    else if(q.question_type==='ORDERING') answers[q.question_id]=q.options?.map(o=>String(o.option_id))||[]
    else if(q.question_type==='MATCHING') answers[q.question_id]=(q.options||[]).filter(o=>o.match_side==='L').map(o=>({left_option_id:String(o.option_id),right_option_id:''}))
    else if(q.question_type==='FILL_BLANK') answers[q.question_id]=Array.from({length:q.keywords?.length||0},()=> '')
    else answers[q.question_id]=''
  }
  // Restore the authoritative saved state before applying any newer local draft.
  for(const q of questions.value){
    if(content.value?.saved_responses?.[q.question_id]!==undefined){
      answers[q.question_id]=content.value.saved_responses[q.question_id]
      lastSaved[q.question_id]=JSON.stringify(answers[q.question_id])
      transmitted[q.question_id]=true
    }
  }
  if(draftKey.value){try{const saved=JSON.parse(sessionStorage.getItem(draftKey.value)||'{}');for(const q of questions.value)if(saved[q.question_id]!==undefined)answers[q.question_id]=saved[q.question_id]}catch{}}
}
function startTimer(isNew=false){
  clearInterval(timer)
  const duration=Number(content.value?.quiz?.duration_minutes||0)*60
  if(!duration){remaining.value=0;return}
  const oracleStarted=content.value?.attempt_started_at
  const oracleMs=oracleStarted ? new Date(oracleStarted).getTime() : NaN
  let started=Number.isFinite(oracleMs) ? oracleMs : Number(sessionStorage.getItem(timerKey.value))
  if(!started){started=Date.now()}
  sessionStorage.setItem(timerKey.value,String(started))
  const tick=()=>{remaining.value=Math.max(0,duration-Math.floor((Date.now()-started)/1000));if(remaining.value<=0&&!submitted.value&&!submitting.value){clearInterval(timer);toast.error('Time is up. Finalizing answers saved before the deadline.');submitQuiz(true)}}
  tick();if(remaining.value>0)timer=setInterval(tick,1000)
}
async function initialize(){
  loading.value=true;error.value=null
  let startedNow=false
  try{
    try {
      content.value=await api.quizzes.content(quizId.value)
      attemptId.value=content.value.attempt_id
    } catch(e) {
      if (!isQuizAttemptRequired(e)) throw e
      const started=await api.quizzes.startAttempt(quizId.value)
      attemptId.value=started.attempt_id
      startedNow=true
      content.value=await api.quizzes.content(quizId.value)
    }
    initializeAnswers();startTimer(startedNow)
  } catch(e) {
    error.value=errorPresentation(e,'quiz')
  } finally { loading.value=false }
}
async function transmitQuestion(q){
  const selected=answers[q.question_id]
  const snapshot=JSON.stringify(selected)
  if(lastSaved[q.question_id]===snapshot)return
  const text=q.question_type==='FILL_BLANK'?(Array.isArray(selected)?selected:null):(['SHORT_TEXT','LONG_TEXT','NUMERICAL'].includes(q.question_type)?String(selected??''):null)
  const payload={question_id:q.question_id,response_text:text}
  if(q.question_type==='ORDERING') payload.ordered_option_ids=(selected||[]).map(String)
  if(q.question_type==='MATCHING') payload.matching_pairs=(selected||[]).filter(x=>x.right_option_id).map(x=>({left_option_id:String(x.left_option_id),right_option_id:String(x.right_option_id)}))
  if(q.question_type==='MCQ_MULTI')payload.selected_option_ids=(selected||[]).map(Number)
  else if(['MCQ_SINGLE','TRUE_FALSE'].includes(q.question_type))payload.selected_option_ids=selected?[Number(selected)]:[]
  await api.quizzes.response(attemptId.value,payload)
  lastSaved[q.question_id]=snapshot
  transmitted[q.question_id]=true
  saveError.value=''
}
function queueAutosave(){
  if(!attemptId.value||submitted.value||submitting.value||loading.value)return
  clearTimeout(autosaveTimer)
  autosaveTimer=setTimeout(()=>{
    if(remaining.value===0 && Number(content.value?.quiz?.duration_minutes||0)>0)return
    const pendingQuestions=questions.value.filter(q=>lastSaved[q.question_id]!==JSON.stringify(answers[q.question_id]))
    saveQueue=saveQueue.catch(()=>{}).then(async()=>{
      for(const q of pendingQuestions)try{await transmitQuestion(q)}catch(e){saveError.value=e.message}
    })
  },650)
}
async function submitQuiz(auto=false){
  confirmSubmit.value=false;submitting.value=true
  clearTimeout(autosaveTimer)
  try{
    // Finish queued autosaves. After time expires, do NOT send late answers:
    // the Oracle server locks them and permits only finalization.
    await saveQueue.catch(()=>{})
    if(!auto && !(remaining.value===0 && Number(content.value?.quiz?.duration_minutes||0)>0)){for(const q of questions.value)await transmitQuestion(q)}
    await api.quizzes.submitAttempt(attemptId.value)
    submitted.value=true;clearInterval(timer);sessionStorage.removeItem(draftKey.value);sessionStorage.removeItem(timerKey.value)
    toast.success(auto?'Quiz auto-submitted.':'Quiz attempt submitted.')
    try{result.value=await api.quizzes.result(attemptId.value)}catch(e){if(e.status!==403)throw e}
    try{review.value=await api.quizzes.review(attemptId.value)}catch(e){if(e.status!==403)throw e}
  }catch(e){toast.error(e.message)}finally{submitting.value=false}
}
function formatFillBlankResponse(value){try{const parsed=JSON.parse(value);return Array.isArray(parsed)?parsed.map((answer,index)=>`Blank ${index+1}: ${answer}`).join(' · '):String(value)}catch{return String(value)}}
function askSubmit(){confirmSubmit.value=true}
function jump(q){document.getElementById(`question-${q.question_id}`)?.scrollIntoView({behavior:'smooth',block:'start'})}

watch(answers,()=>{
  if(draftKey.value&&!submitted.value)sessionStorage.setItem(draftKey.value,JSON.stringify(answers))
  // Clear the saved badge whenever the answer differs from the last committed version.
  for(const q of questions.value)if(lastSaved[q.question_id]!==JSON.stringify(answers[q.question_id]))transmitted[q.question_id]=false
  queueAutosave()
},{deep:true})
onMounted(initialize)
onUnmounted(()=>{clearInterval(timer);clearTimeout(autosaveTimer)})
</script>

<template>
  <AppShell>
    <template #title>Quiz Attempt</template>
    <ErrorState v-if="error" :title="error.title" :message="error.message" :retryable="error.retryable" @retry="initialize" @back="router.back()" />
    <LoadingState v-else-if="loading" message="Preparing quiz attempt…" />
    <template v-else-if="content">
      <div class="page-heading"><div><div class="eyebrow">Assessment attempt</div><h1>{{content.quiz?.quiz_title}}</h1><p>{{content.question_count}} question(s) · {{content.quiz?.duration_minutes||'—'}} minutes · Maximum {{content.quiz?.max_marks||'—'}} marks</p></div><button class="btn btn-soft" @click="router.back()">Back</button></div>

      <template v-if="!submitted">
        <div class="quiz-status-bar">
          <div><span class="quiz-status-label">Progress</span><strong>{{answeredCount}} / {{questions.length}} answered</strong><div class="progress-track" role="progressbar" :aria-valuenow="progressPercent" aria-valuemin="0" aria-valuemax="100" :aria-label="`${progressPercent}% of questions answered`"><div class="progress-fill" :style="{width:`${progressPercent}%`}"></div></div><span class="quiz-progress-caption">{{ progressPercent }}% complete</span></div>
          <div class="quiz-timer" :class="`timer-${timerTone}`"><span>Time remaining</span><strong>{{timeLabel}}</strong></div>
        </div>
        <div class="notice notice-info" style="margin-bottom:18px">Your answers are autosaved to EduSphere while the quiz is open. At timeout, only successfully saved answers are submitted.</div><div v-if="saveError" class="notice notice-error" role="alert">Autosave error: {{saveError}}. Review your network connection before submitting.</div>

        <div class="quiz-layout">
          <aside class="quiz-nav-panel"><strong>Questions</strong><div class="quiz-nav-grid"><button v-for="q in questions" :key="q.question_id" class="quiz-nav-button" :class="{answered:answered(q),sent:transmitted[q.question_id]}" :aria-label="`Go to question ${q.question_order}${answered(q) ? ' (answered)' : ' (unanswered)'}`" @click="jump(q)">{{q.question_order}}</button></div><div class="quiz-nav-legend"><span><i class="legend-dot answered"></i>Answered</span><span><i class="legend-dot"></i>Unanswered</span></div></aside>
          <div>
            <article v-for="q in questions" :id="`question-${q.question_id}`" :key="q.question_id" class="quiz-question">
              <div class="quiz-question-head"><div class="question-number">{{q.question_order}}</div><div><strong>{{q.question_text}}</strong><div class="course-meta">{{q.question_marks}} mark(s) · {{ displayLabel(q.question_type) }}</div></div><StatusBadge v-if="transmitted[q.question_id]" value="SENT" style="margin-left:auto" /></div>
              <div v-if="['MCQ_SINGLE','TRUE_FALSE'].includes(q.question_type)" class="option-list"><label v-for="o in q.options" :key="o.option_id" class="option-row"><input v-model="answers[q.question_id]" type="radio" :name="`q${q.question_id}`" :value="String(o.option_id)"/><span>{{o.option_text}}</span></label></div>
              <div v-else-if="q.question_type==='MCQ_MULTI'" class="option-list"><label v-for="o in q.options" :key="o.option_id" class="option-row"><input v-model="answers[q.question_id]" type="checkbox" :value="String(o.option_id)"/><span>{{o.option_text}}</span></label></div>
              <div v-else-if="q.question_type==='ORDERING'" class="option-list">
                <div v-for="(option,index) in (answers[q.question_id]||[])" :key="option" class="option-row">
                  <strong>{{index+1}}</strong><span>{{q.options.find(o=>String(o.option_id)===String(option))?.option_text}}</span>
                  <div style="margin-left:auto;display:flex;gap:6px">
                    <button type="button" class="btn btn-soft btn-sm" :disabled="index===0||submitting||remaining===0" @click="answers[q.question_id].splice(index-1,0,answers[q.question_id].splice(index,1)[0])">↑</button>
                    <button type="button" class="btn btn-soft btn-sm" :disabled="index===answers[q.question_id].length-1||submitting||remaining===0" @click="answers[q.question_id].splice(index+1,0,answers[q.question_id].splice(index,1)[0])">↓</button>
                  </div>
                </div>
              </div>
              <div v-else-if="q.question_type==='FILL_BLANK'" class="option-list"><div v-for="(keyword,index) in (q.keywords||[])" :key="keyword.keyword_order" class="option-row"><strong>Blank {{index+1}}</strong><input v-model="answers[q.question_id][index]" class="input" :placeholder="`Answer for blank ${index+1}`" /></div></div>
              <div v-else-if="q.question_type==='MATCHING'" class="option-list">
                <div v-for="item in (answers[q.question_id]||[])" :key="item.left_option_id" class="option-row">
                  <span style="min-width:180px">{{q.options.find(o=>String(o.option_id)===String(item.left_option_id))?.option_text}}</span>
                  <select v-model="item.right_option_id" class="select" :aria-label="`Match for ${q.options.find(o=>String(o.option_id)===String(item.left_option_id))?.option_text || 'left item'}`">
                    <option value="" disabled>Select match</option>
                    <option v-for="o in q.options.filter(x=>x.match_side==='R')" :key="o.option_id" :value="String(o.option_id)">{{o.option_text}}</option>
                  </select>
                </div>
              </div>
              <textarea v-else v-model="answers[q.question_id]" class="textarea" placeholder="Type your answer"></textarea>
              <div class="draft-indicator">{{transmitted[q.question_id]?'Saved to Oracle.':'Unsaved draft · autosaving'}}</div>
            </article>
            <div class="section-card quiz-submit-bar"><div><strong>{{unansweredCount ? `${unansweredCount} unanswered question(s)` : 'All questions answered'}}</strong><span>Review your answers before final submission.</span></div><button class="btn btn-primary" :disabled="submitting" @click="askSubmit">{{submitting?'Submitting…':'Submit quiz attempt'}}</button></div>
          </div>
        </div>
      </template>

      <template v-else>
        <SectionCard title="Attempt submitted" subtitle="Marks and answer review appear only when the instructor has enabled the corresponding visibility controls."><div v-if="result" class="stats-grid" style="margin-bottom:0"><div class="stat-card"><div><div class="stat-label">Marks obtained</div><div class="stat-value">{{result.marks_obtained??'—'}}</div></div></div><div class="stat-card"><div><div class="stat-label">Maximum marks</div><div class="stat-value">{{result.max_marks??'—'}}</div></div></div></div><div v-else class="notice notice-info">Marks are currently hidden by the instructor.</div></SectionCard>
        <SectionCard title="Answer review"><div v-if="review?.questions?.length"><article v-for="q in review.questions" :key="q.question_id" class="quiz-question"><strong>{{q.question_order}}. {{q.question_text}}</strong><div v-if="q.response_text" class="notice notice-info" style="margin-top:10px">Your response: {{q.question_type==='FILL_BLANK' ? formatFillBlankResponse(q.response_text) : q.response_text}}</div><div v-if="q.options?.length" class="option-list" style="margin-top:10px"><div v-for="o in q.options" :key="o.option_id" class="option-row"><StatusBadge :value="o.is_correct"/><span>{{o.option_text}}</span><strong v-if="o.is_selected" style="margin-left:auto">Selected</strong></div></div></article></div><div v-else class="notice notice-info">Answer review is currently hidden by the instructor.</div></SectionCard>
      </template>
    </template>
    <ConfirmDialog :open="confirmSubmit" title="Submit quiz attempt?" :message="unansweredCount ? `${unansweredCount} question(s) are unanswered. They will be submitted without a selected/text answer. This action is final.` : 'All questions are answered. This action is final.'" confirm-label="Submit attempt" :busy="submitting" @cancel="confirmSubmit=false" @confirm="submitQuiz(false)" />
  </AppShell>
</template>
