<script setup>
import { reactive, ref } from 'vue'
import SectionCard from '../SectionCard.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
import { formatDate, ATTENDANCE_STATUSES, SESSION_TYPES, displayLabel } from '../../utils/format.js'
const props=defineProps({sessions:{type:Array,default:()=>[]},roster:{type:Array,default:()=>[]},canRecord:{type:Boolean,default:true},blockedMessage:{type:String,default:''}})
const emit=defineEmits(['refresh'])
const pending=ref(false)
const form=reactive({session_id:'',student_id:'',attendance_status:'PRESENT',remarks:''})
async function submit(){pending.value=true;try{await api.attendance.record({session_id:Number(form.session_id),student_id:Number(form.student_id),attendance_status:form.attendance_status,remarks:form.remarks});toast.success('Attendance recorded.');form.remarks='';emit('refresh')}catch(e){toast.error(e.message)}finally{pending.value=false}}
</script>
<template>
  <div v-if="!canRecord && blockedMessage" class="notice notice-info">{{ blockedMessage }}</div>
  <SectionCard v-if="canRecord" title="Record attendance"><form class="form-grid form-grid-3" @submit.prevent="submit"><div class="field"><label>Class session</label><select v-model="form.session_id" class="select" required><option value="" disabled>Select session</option><option v-for="s in sessions" :key="s.session_id" :value="s.session_id">{{formatDate(s.session_date)}} · {{s.start_time}} · {{s.topic||displayLabel(s.session_type)}}</option></select></div><div class="field"><label>Student</label><select v-model="form.student_id" class="select" required><option value="" disabled>Select student</option><option v-for="s in roster" :key="s.student_id" :value="s.student_id">{{s.student_name}} · {{s.admission_no}}</option></select></div><div class="field"><label>Status</label><select v-model="form.attendance_status" class="select"><option v-for="x in ATTENDANCE_STATUSES" :key="x" :value="x">{{ displayLabel(x) }}</option></select></div><div class="field full"><label>Remarks</label><input v-model="form.remarks" class="input" /></div><div class="field full"><button class="btn btn-primary" type="submit" :disabled="pending||!sessions.length||!roster.length">{{pending?'Saving…':'Record attendance'}}</button></div></form></SectionCard>
</template>
