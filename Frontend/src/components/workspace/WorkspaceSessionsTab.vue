<script setup>
import { computed, reactive, ref } from 'vue'
import SectionCard from '../SectionCard.vue'
import DataTable from '../DataTable.vue'
import CalendarMonth from '../CalendarMonth.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
import StatusBadge from '../StatusBadge.vue'
import { SESSION_TYPES, displayLabel } from '../../utils/format.js'
const props=defineProps({offeringId:Number,sessions:{type:Array,default:()=>[]},canCreate:Boolean,blockedMessage:{type:String,default:''}})
const emit=defineEmits(['refresh'])
const pending=ref(false)
const form=reactive({session_date:'',start_time:'',end_time:'',session_type:'LECTURE',topic:''})
const events=computed(()=>props.sessions.map(s=>({key:s.session_id,date:s.session_date,label:`${s.start_time||''} ${s.topic||s.session_type||'Class'}`.trim(),detail:`${s.topic||s.session_type||'Class'} · ${s.start_time||'—'}${s.end_time?`–${s.end_time}`:''}`})))
async function create(){if(form.end_time&&form.start_time&&form.end_time<=form.start_time){toast.error('End time must be after start time.');return}pending.value=true;try{await api.attendance.createSession({offering_id:props.offeringId,...form});toast.success('Class session created.');Object.assign(form,{session_date:'',start_time:'',end_time:'',session_type:'LECTURE',topic:''});emit('refresh')}catch(e){toast.error(e.message)}finally{pending.value=false}}
</script>
<template>
  <div v-if="!canCreate && blockedMessage" class="notice notice-info">{{ blockedMessage }}</div>
  <SectionCard v-if="canCreate" title="Create class session">
    <form class="form-grid form-grid-3" @submit.prevent="create">
      <div class="field"><label>Date</label><input v-model="form.session_date" type="date" class="input" required /></div>
      <div class="field"><label>Start time</label><input v-model="form.start_time" type="time" class="input" required /></div>
      <div class="field"><label>End time</label><input v-model="form.end_time" type="time" class="input" /></div>
      <div class="field"><label>Session type</label><select v-model="form.session_type" class="select"><option v-for="x in SESSION_TYPES" :key="x" :value="x">{{ displayLabel(x) }}</option></select></div>
      <div class="field" style="grid-column:span 2"><label>Topic</label><input v-model="form.topic" class="input" /></div>
      <div class="field full"><button class="btn btn-primary" type="submit" :disabled="pending">{{pending?'Creating…':'Create session'}}</button></div>
    </form>
  </SectionCard>
  <div class="grid grid-2 calendar-table-grid"><CalendarMonth :events="events" title="Class calendar" /><SectionCard title="Class sessions"><DataTable :rows="sessions" :columns="[{key:'session_date',label:'Date'},{key:'start_time',label:'Start'},{key:'end_time',label:'End'},{key:'session_type',label:'Session type'},{key:'topic',label:'Topic'}]"><template #cell-session_type="{value}"><StatusBadge :value="value" /></template></DataTable></SectionCard></div>
</template>
