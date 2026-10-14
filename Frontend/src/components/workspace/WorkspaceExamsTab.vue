<script setup>
import { computed, reactive, ref } from 'vue'
import SectionCard from '../SectionCard.vue'
import DataTable from '../DataTable.vue'
import CalendarMonth from '../CalendarMonth.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
import { EXAM_TYPES, displayLabel } from '../../utils/format.js'
const props=defineProps({exams:{type:Array,default:()=>[]},examComponents:{type:Array,default:()=>[]},canCreate:Boolean,blockedMessage:{type:String,default:''}})
const emit=defineEmits(['refresh'])
const pending=ref(false)
const form=reactive({component_id:'',exam_title:'',exam_type:'FINAL',exam_date:'',start_time:'',end_time:''})
const events=computed(()=>props.exams.map(e=>({key:e.exam_id,date:e.exam_date,label:`${e.start_time||''} ${e.exam_title||'Exam'}`.trim(),detail:`${e.course_code||''} ${e.exam_title||'Exam'} · ${e.exam_type||''} · ${e.start_time||'—'}${e.end_time?`–${e.end_time}`:''}`})))
async function create(){if(form.end_time&&form.start_time&&form.end_time<=form.start_time){toast.error('Exam end time must be after start time.');return}pending.value=true;try{await api.exams.schedule({...form});toast.success('Exam scheduled.');Object.assign(form,{component_id:'',exam_title:'',exam_type:'FINAL',exam_date:'',start_time:'',end_time:''});emit('refresh')}catch(e){toast.error(e.message)}finally{pending.value=false}}
</script>
<template>
  <div v-if="!canCreate && blockedMessage" class="notice notice-info">{{ blockedMessage }}</div>
  <SectionCard v-if="canCreate && examComponents.length" title="Schedule exam">
    <form class="form-grid form-grid-3" @submit.prevent="create">
      <div class="field"><label>Assessment</label><select v-model="form.component_id" class="select" required><option value="" disabled>Select assessment</option><option v-for="c in examComponents" :key="c.component_id" :value="c.component_id">{{c.component_name}} · {{c.max_marks}} marks</option></select></div>
      <div class="field"><label>Exam title</label><input v-model="form.exam_title" class="input" required /></div>
      <div class="field"><label>Type</label><select v-model="form.exam_type" class="select"><option v-for="x in EXAM_TYPES" :key="x" :value="x">{{ displayLabel(x) }}</option></select></div>
      <div class="field"><label>Date</label><input v-model="form.exam_date" type="date" class="input" required /></div>
      <div class="field"><label>Start time</label><input v-model="form.start_time" type="time" class="input" /></div>
      <div class="field"><label>End time</label><input v-model="form.end_time" type="time" class="input" /></div>
      <div class="field full"><button class="btn btn-primary" type="submit" :disabled="pending">{{pending?'Scheduling…':'Schedule exam'}}</button></div>
    </form>
  </SectionCard>
  <div v-else-if="canCreate && !examComponents.length" class="notice notice-info">All exam assessments for this class are already configured.</div>
  <div class="grid grid-2 calendar-table-grid"><CalendarMonth :events="events" title="Exam calendar" /><SectionCard title="Exam schedule"><DataTable :rows="exams" :columns="[{key:'exam_title',label:'Exam'},{key:'exam_type',label:'Type'},{key:'exam_date',label:'Date'},{key:'start_time',label:'Start'},{key:'end_time',label:'End'}]"><template #cell-exam_type="{value}"><span>{{ displayLabel(value) }}</span></template></DataTable></SectionCard></div>
</template>
