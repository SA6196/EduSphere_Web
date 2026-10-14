<script setup>
import { computed, reactive, ref } from 'vue'
import SectionCard from '../SectionCard.vue'
import DataTable from '../DataTable.vue'
import FileUrlField from '../FileUrlField.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import StatusBadge from '../StatusBadge.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
const props=defineProps({
  assignments:{type:Array,default:()=>[]},
  assignmentComponents:{type:Array,default:()=>[]},
  roster:{type:Array,default:()=>[]},
  isInstructor:Boolean,
  isStudent:Boolean,
  canCreate:{type:Boolean,default:true},
  canSubmit:{type:Boolean,default:true},
  createBlockedMessage:{type:String,default:''},
  submitBlockedMessage:{type:String,default:''},
})
const emit=defineEmits(['refresh'])
const creating=ref(false), submitting=ref(false), reviewRows=ref([]), reviewTitle=ref('')
const confirmOpen=ref(false)
const createForm=reactive({component_id:'',assignment_title:'',assignment_description:'',due_date:'',allow_resubmission:'N'})
const submitForm=reactive({assignment_id:'',file_url:''})
const rosterByStudentId=computed(()=>new Map(props.roster.map(s=>[String(s.student_id),s])))
const reviewDisplayRows=computed(()=>reviewRows.value.map(r=>({
  ...r,
  student_name:rosterByStudentId.value.get(String(r.student_id))?.student_name || 'Student name unavailable',
  admission_no:rosterByStudentId.value.get(String(r.student_id))?.admission_no || '—',
})))
async function create(){creating.value=true;try{await api.assignments.create({...createForm,due_date:createForm.due_date?`${createForm.due_date}:00`:''});toast.success('Assignment created.');Object.assign(createForm,{component_id:'',assignment_title:'',assignment_description:'',due_date:'',allow_resubmission:'N'});emit('refresh')}catch(e){toast.error(e.message)}finally{creating.value=false}}
async function submit(){confirmOpen.value=false;submitting.value=true;try{await api.assignments.submit(Number(submitForm.assignment_id),submitForm.file_url);toast.success('Assignment submitted.');Object.assign(submitForm,{assignment_id:'',file_url:''});emit('refresh')}catch(e){toast.error(e.message)}finally{submitting.value=false}}
async function review(row){try{const data=await api.assignments.review(row.assignment_id);reviewRows.value=Array.isArray(data)?data:(data?.results||data?.items||[]);reviewTitle.value=row.assignment_title||'Assignment'}catch(e){toast.error(e.message)}}
</script>
<template>
  <div v-if="isInstructor && !canCreate && createBlockedMessage" class="notice notice-info">{{ createBlockedMessage }}</div>
  <SectionCard v-if="isInstructor && canCreate && assignmentComponents.length" title="Create assignment">
    <form class="form-grid" @submit.prevent="create">
      <div class="field"><label>Assessment</label><select v-model="createForm.component_id" class="select" required><option value="" disabled>Select assessment</option><option v-for="c in assignmentComponents" :key="c.component_id" :value="c.component_id">{{c.component_name}} · {{c.max_marks}} marks</option></select></div>
      <div class="field"><label>Due date & time</label><input v-model="createForm.due_date" type="datetime-local" class="input" required /></div>
      <div class="field"><label>Title</label><input v-model="createForm.assignment_title" class="input" required /></div>
      <div class="field"><label>Allow resubmission</label><select v-model="createForm.allow_resubmission" class="select"><option value="Y">Yes</option><option value="N">No</option></select></div>
      <div class="field full"><label>Description</label><textarea v-model="createForm.assignment_description" class="textarea" /></div>
      <div class="field full"><button class="btn btn-primary" type="submit" :disabled="creating">{{creating?'Creating…':'Create assignment'}}</button></div>
    </form>
  </SectionCard>
  <div v-else-if="isInstructor && canCreate && !assignmentComponents.length" class="notice notice-info">All assignment assessments for this class are already configured.</div>

  <div v-if="isStudent && !canSubmit && submitBlockedMessage" class="notice notice-info">{{ submitBlockedMessage }}</div>
  <SectionCard v-if="isStudent && canSubmit && assignments.length" title="Submit assignment">
    <form class="form-grid" @submit.prevent="confirmOpen=true">
      <div class="field"><label>Assignment</label><select v-model="submitForm.assignment_id" class="select" required><option value="" disabled>Select assignment</option><option v-for="a in assignments" :key="a.assignment_id" :value="a.assignment_id">{{a.assignment_title}} · due {{a.due_date ? new Date(a.due_date).toLocaleString() : '—'}}</option></select></div>
      <FileUrlField v-model="submitForm.file_url" label="Submission URL" required />
      <div class="field full"><button class="btn btn-primary" type="submit" :disabled="submitting">{{submitting?'Submitting…':'Review & submit'}}</button></div>
    </form>
  </SectionCard>

  <SectionCard title="Assignments"><DataTable :rows="assignments" :columns="[{key:'assignment_title',label:'Assignment'},{key:'assignment_description',label:'Description'},{key:'due_date',label:'Due',type:'datetime'},{key:'allow_resubmission',label:'Resubmission'},{key:'component_name',label:'Component'}]"><template #cell-allow_resubmission="{value}"><StatusBadge :value="value" /></template><template v-if="isInstructor" #actions="{row}"><button class="btn btn-soft btn-sm" @click="review(row)">Review submissions</button></template></DataTable></SectionCard>

  <SectionCard v-if="reviewRows.length||reviewTitle" :title="`Submissions — ${reviewTitle}`"><DataTable :rows="reviewDisplayRows" :columns="[{key:'student_name',label:'Student'},{key:'admission_no',label:'Admission No.'},{key:'submission_version',label:'Version'},{key:'submitted_at',label:'Submitted'},{key:'file_url',label:'Submission'},{key:'submission_status',label:'Status'},{key:'feedback',label:'Feedback'}]"><template #cell-file_url="{value}"><a v-if="value" :href="value" target="_blank" rel="noreferrer" class="table-link">Open submission</a><span v-else>—</span></template><template #cell-submission_status="{value}"><StatusBadge :value="value" /></template></DataTable></SectionCard>
  <ConfirmDialog :open="confirmOpen" title="Submit assignment?" message="This creates a new submission version using the hosted URL you entered." confirm-label="Submit assignment" :busy="submitting" @cancel="confirmOpen=false" @confirm="submit" />
</template>
