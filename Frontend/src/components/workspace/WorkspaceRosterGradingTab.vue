<script setup>
import { computed, reactive, ref, watch } from 'vue'
import SectionCard from '../SectionCard.vue'
import DataTable from '../DataTable.vue'
import StatusBadge from '../StatusBadge.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
import { displayLabel } from '../../utils/format.js'
const props=defineProps({components:{type:Array,default:()=>[]},roster:{type:Array,default:()=>[]},assignments:{type:Array,default:()=>[]}})
const emit=defineEmits(['refresh'])
const form=reactive({component_id:'',enrollment_id:'',marks_obtained:'',graded_submission_id:''})
const submissions=ref([]), loadingSubs=ref(false), pending=ref(false), publishBusy=ref(false)
const confirm=reactive({open:false,row:null})
const selectedComponent=computed(()=>props.components.find(c=>String(c.component_id)===String(form.component_id)))
const selectedStudent=computed(()=>props.roster.find(s=>String(s.enrollment_id)===String(form.enrollment_id)))
const isAssignment=computed(()=>selectedComponent.value?.component_type==='ASSIGNMENT')
async function loadSubmissions(){submissions.value=[];form.graded_submission_id='';if(!isAssignment.value||!selectedStudent.value)return;const assignment=props.assignments.find(a=>String(a.component_id)===String(form.component_id));if(!assignment)return;loadingSubs.value=true;try{const data=await api.assignments.review(assignment.assignment_id);const rows=Array.isArray(data)?data:(data?.results||data?.items||[]);submissions.value=rows.filter(r=>String(r.enrollment_id||'')===String(form.enrollment_id)||String(r.student_id||'')===String(selectedStudent.value.student_id))}catch(e){toast.error(e.message)}finally{loadingSubs.value=false}}
watch(()=>[form.component_id,form.enrollment_id],loadSubmissions)
async function record(){pending.value=true;try{const payload={component_id:Number(form.component_id),enrollment_id:Number(form.enrollment_id),marks_obtained:Number(form.marks_obtained)};if(isAssignment.value&&form.graded_submission_id)payload.graded_submission_id=Number(form.graded_submission_id);await api.academics.recordMark(payload);toast.success('Mark recorded.');form.marks_obtained='';emit('refresh')}catch(e){toast.error(e.message)}finally{pending.value=false}}
function askPublish(row){confirm.open=true;confirm.row=row}
async function publish(){const row=confirm.row;confirm.open=false;publishBusy.value=true;try{await api.academics.publishGrade(row.enrollment_id);toast.success('Grade published.');emit('refresh')}catch(e){toast.error(e.message)}finally{publishBusy.value=false}}
</script>
<template>
  <SectionCard title="Record / update mark" subtitle="Select a named assessment and student. Assignment submission versions are resolved automatically.">
    <form class="form-grid form-grid-3" @submit.prevent="record">
      <div class="field"><label>Assessment</label><select v-model="form.component_id" class="select" required><option value="" disabled>Select assessment</option><option v-for="c in components" :key="c.component_id" :value="c.component_id">{{c.component_name}} · {{displayLabel(c.component_type)}} · max {{c.max_marks}}</option></select></div>
      <div class="field"><label>Student</label><select v-model="form.enrollment_id" class="select" required><option value="" disabled>Select student</option><option v-for="s in roster" :key="s.enrollment_id" :value="s.enrollment_id">{{s.student_name}} · {{s.admission_no}}</option></select></div>
      <div class="field"><label>Marks obtained</label><input v-model="form.marks_obtained" type="number" step="0.01" min="0" :max="selectedComponent?.max_marks||undefined" class="input" required /></div>
      <div v-if="isAssignment" class="field"><label>Assignment submission</label><select v-model="form.graded_submission_id" class="select" :disabled="loadingSubs" required><option value="" disabled>{{loadingSubs?'Loading submissions…':'Select submitted version'}}</option><option v-for="s in submissions" :key="s.submission_id" :value="s.submission_id">Version {{s.submission_version||'—'}} · {{s.submission_status||'SUBMITTED'}} · {{s.submitted_at?new Date(s.submitted_at).toLocaleString():''}}</option></select><span v-if="!loadingSubs&&!submissions.length&&selectedStudent" class="help">No submission found for this student/component.</span></div>
      <div class="field" style="align-self:end"><button class="btn btn-primary" type="submit" :disabled="pending||loadingSubs">{{pending?'Saving…':'Record mark'}}</button></div>
    </form>
  </SectionCard>
  <SectionCard title="Class roster"><DataTable :rows="roster" :columns="[{key:'admission_no',label:'Admission no'},{key:'student_name',label:'Student'},{key:'batch',label:'Batch'},{key:'student_status',label:'Student status'},{key:'enrollment_date',label:'Enrolled on'},{key:'enrollment_status',label:'Enrollment'}]"><template #cell-student_status="{value}"><StatusBadge :value="value" /></template><template #cell-enrollment_status="{value}"><StatusBadge :value="value" /></template><template #actions="{row}"><button class="btn btn-success btn-sm" :disabled="publishBusy" @click="askPublish(row)">Publish grade</button></template></DataTable></SectionCard>
  <ConfirmDialog :open="confirm.open" title="Publish final grade?" :message="`Publish the final grade for ${confirm.row?.student_name||'this student'}? Oracle will require a complete 100% grading scheme and all weighted marks.`" confirm-label="Publish grade" :busy="publishBusy" @cancel="confirm.open=false" @confirm="publish" />
</template>
