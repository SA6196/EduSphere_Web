<script setup>
import { reactive, ref } from 'vue'
import SectionCard from '../SectionCard.vue'
import DataTable from '../DataTable.vue'
import StatusBadge from '../StatusBadge.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
const props=defineProps({quizzes:{type:Array,default:()=>[]},quizComponents:{type:Array,default:()=>[]},isInstructor:Boolean,isStudent:Boolean,canCreate:{type:Boolean,default:true},createBlockedMessage:{type:String,default:''}})
const emit=defineEmits(['refresh'])
const creating=ref(false), visibilityBusy=ref(false), confirm=reactive({open:false,quiz:null,field:''})
const form=reactive({component_id:'',quiz_title:'',open_at:'',close_at:'',duration_minutes:30,max_attempts:1})
async function create(){if(form.open_at&&form.close_at&&form.close_at<=form.open_at){toast.error('Quiz close time must be after open time.');return}creating.value=true;try{await api.quizzes.create({...form,open_at:form.open_at?`${form.open_at}:00`:null,close_at:form.close_at?`${form.close_at}:00`:null});toast.success('Quiz created.');Object.assign(form,{component_id:'',quiz_title:'',open_at:'',close_at:'',duration_minutes:30,max_attempts:1});emit('refresh')}catch(e){toast.error(e.message)}finally{creating.value=false}}
function askVisibility(q,field){Object.assign(confirm,{open:true,quiz:q,field})}
async function applyVisibility(){const q=confirm.quiz,field=confirm.field;confirm.open=false;visibilityBusy.value=true;try{await api.quizzes.visibility(q.quiz_id,{allow_mark_view:field==='mark'?(q.allow_mark_view==='Y'?'N':'Y'):q.allow_mark_view,allow_answer_review:field==='review'?(q.allow_answer_review==='Y'?'N':'Y'):q.allow_answer_review});toast.success('Quiz visibility updated.');emit('refresh')}catch(e){toast.error(e.message)}finally{visibilityBusy.value=false}}
</script>
<template>
  <div v-if="isInstructor && !canCreate && createBlockedMessage" class="notice notice-info">{{ createBlockedMessage }}</div>
  <SectionCard v-if="isInstructor && canCreate && quizComponents.length" title="Create quiz">
    <form class="form-grid form-grid-3" @submit.prevent="create">
      <div class="field"><label>Assessment</label><select v-model="form.component_id" class="select" required><option value="" disabled>Select assessment</option><option v-for="c in quizComponents" :key="c.component_id" :value="c.component_id">{{c.component_name}} · {{c.max_marks}} marks</option></select></div>
      <div class="field"><label>Title</label><input v-model="form.quiz_title" class="input" required /></div>
      <div class="field"><label>Max attempts</label><input v-model.number="form.max_attempts" type="number" min="1" class="input" /></div>
      <div class="field"><label>Open at</label><input v-model="form.open_at" type="datetime-local" class="input" /></div>
      <div class="field"><label>Close at</label><input v-model="form.close_at" type="datetime-local" class="input" /></div>
      <div class="field"><label>Duration (minutes)</label><input v-model.number="form.duration_minutes" type="number" min="1" class="input" /></div>
      <div class="field full" style="display:flex;gap:8px"><button class="btn btn-primary" type="submit" :disabled="creating">{{creating?'Creating…':'Create quiz'}}</button><RouterLink class="btn btn-secondary" to="/question-bank">Open question bank</RouterLink></div>
    </form>
  </SectionCard>
  <div v-else-if="isInstructor && canCreate && !quizComponents.length" class="notice notice-info">All quiz assessments for this class are already configured.</div>
  <SectionCard title="Quizzes">
    <DataTable :rows="quizzes" :columns="[{key:'quiz_title',label:'Quiz'},{key:'open_at',label:'Open'},{key:'close_at',label:'Close'},{key:'duration_minutes',label:'Minutes'},{key:'max_attempts',label:'Attempts'},{key:'allow_mark_view',label:'Marks visible'},{key:'allow_answer_review',label:'Review visible'}]">
      <template #cell-allow_mark_view="{value}"><StatusBadge :value="value" /></template><template #cell-allow_answer_review="{value}"><StatusBadge :value="value" /></template>
      <template #actions="{row}"><RouterLink v-if="isStudent" class="btn btn-primary btn-sm" :to="`/student/quizzes/${row.quiz_id}`">Take quiz</RouterLink><template v-else><RouterLink class="btn btn-soft btn-sm" :to="`/instructor/quizzes/${row.quiz_id}/grading`">Review auto grades</RouterLink><button class="btn btn-soft btn-sm" :disabled="visibilityBusy" @click="askVisibility(row,'mark')">{{ row.allow_mark_view==='Y' ? 'Hide marks' : 'Show marks' }}</button><button class="btn btn-soft btn-sm" :disabled="visibilityBusy" @click="askVisibility(row,'review')">{{ row.allow_answer_review==='Y' ? 'Disable answer review' : 'Allow answer review' }}</button></template></template>
    </DataTable>
  </SectionCard>
  <ConfirmDialog :open="confirm.open" title="Change quiz visibility?" :message="`This will ${confirm.field==='mark'?'change student mark visibility':'change answer-review visibility'} for ${confirm.quiz?.quiz_title||'this quiz'}.`" confirm-label="Apply change" :busy="visibilityBusy" @cancel="confirm.open=false" @confirm="applyVisibility" />
</template>
