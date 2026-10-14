<script setup>
import { reactive, ref } from 'vue'
import SectionCard from '../SectionCard.vue'
import DataTable from '../DataTable.vue'
import StatusBadge from '../StatusBadge.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
import { displayLabel } from '../../utils/format.js'
const props=defineProps({offeringId:Number,announcements:{type:Array,default:()=>[]},canCreate:Boolean,blockedMessage:{type:String,default:''}})
const emit=defineEmits(['refresh'])
const pending=ref(false)
const form=reactive({announcement_title:'',announcement_message:'',announcement_priority:'NORMAL'})
async function create(){pending.value=true;try{await api.announcements.create({offering_id:props.offeringId,...form});toast.success('Announcement posted.');Object.assign(form,{announcement_title:'',announcement_message:'',announcement_priority:'NORMAL'});emit('refresh')}catch(e){toast.error(e.message)}finally{pending.value=false}}
</script>
<template>
  <div v-if="!canCreate && blockedMessage" class="notice notice-info">{{ blockedMessage }}</div>
  <SectionCard v-if="canCreate" title="Post announcement">
    <form class="form-grid" @submit.prevent="create">
      <div class="field"><label>Title</label><input v-model="form.announcement_title" class="input" required /></div>
      <div class="field"><label>Priority</label><select v-model="form.announcement_priority" class="select"><option v-for="x in ['LOW','NORMAL','HIGH','URGENT']" :key="x" :value="x">{{displayLabel(x)}}</option></select></div>
      <div class="field full"><label>Message</label><textarea v-model="form.announcement_message" class="textarea" required /></div>
      <div class="field full"><button class="btn btn-primary" type="submit" :disabled="pending">{{pending?'Posting…':'Post announcement'}}</button></div>
    </form>
  </SectionCard>
  <SectionCard title="Announcements"><DataTable :rows="announcements" :columns="[{key:'announcement_title',label:'Title'},{key:'announcement_message',label:'Message'},{key:'announcement_priority',label:'Priority'},{key:'posted_by_username',label:'Posted by'},{key:'posted_at',label:'Posted'}]"><template #cell-announcement_priority="{value}"><StatusBadge :value="value" /></template></DataTable></SectionCard>
</template>
