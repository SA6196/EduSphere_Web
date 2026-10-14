<script setup>
import { reactive, ref } from 'vue'
import SectionCard from '../SectionCard.vue'
import DataTable from '../DataTable.vue'
import FileUrlField from '../FileUrlField.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
import StatusBadge from '../StatusBadge.vue'
import { MATERIAL_TYPES, displayLabel } from '../../utils/format.js'
const props=defineProps({offeringId:Number,materials:{type:Array,default:()=>[]},canCreate:Boolean,blockedMessage:{type:String,default:''}})
const emit=defineEmits(['refresh'])
const pending=ref(false)
const form=reactive({material_title:'',material_type:'PDF',material_url:''})
async function create(){pending.value=true;try{await api.materials.create({offering_id:props.offeringId,...form});toast.success('Material created.');Object.assign(form,{material_title:'',material_type:'PDF',material_url:''});emit('refresh')}catch(e){toast.error(e.message)}finally{pending.value=false}}
</script>
<template>
  <div v-if="!canCreate && blockedMessage" class="notice notice-info">{{ blockedMessage }}</div>
  <SectionCard v-if="canCreate" title="Add course material">
    <form class="form-grid form-grid-3" @submit.prevent="create">
      <div class="field"><label>Title</label><input v-model="form.material_title" class="input" required /></div>
      <div class="field"><label>Type</label><select v-model="form.material_type" class="select"><option v-for="x in MATERIAL_TYPES" :key="x" :value="x">{{ displayLabel(x) }}</option></select></div>
      <div class="field"><label>Storage</label><div class="notice notice-info">Hosted resource link</div></div>
      <FileUrlField v-model="form.material_url" label="Resource URL" />
      <div class="field full"><button class="btn btn-primary" type="submit" :disabled="pending">{{pending?'Creating…':'Create material'}}</button></div>
    </form>
  </SectionCard>
  <SectionCard title="Course materials">
    <DataTable :rows="materials" :columns="[{key:'material_title',label:'Title'},{key:'material_type',label:'Material type'},{key:'uploaded_at',label:'Uploaded'},{key:'material_url',label:'Resource'}]">
      <template #cell-material_type="{value}"><StatusBadge :value="value" /></template><template #cell-material_url="{ value }"><a v-if="value" :href="value" target="_blank" rel="noreferrer" class="table-link">Open resource</a><span v-else>—</span></template>
    </DataTable>
  </SectionCard>
</template>
