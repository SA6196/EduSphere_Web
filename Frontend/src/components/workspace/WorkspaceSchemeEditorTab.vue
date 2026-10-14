<script setup>
import { onMounted, ref, reactive, computed } from 'vue'
import SectionCard from '../SectionCard.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
const props=defineProps({offeringId:{type:Number,required:true}})
const emit=defineEmits(['refresh'])
const busy=ref(false), result=ref(null), schemeName=ref(''), items=ref([])
const locked=computed(()=>Number(result.value?.published_grade_count||0)>0)
const total=computed(()=>items.value.reduce((s,x)=>s+Number(x.weight_percentage||0),0))
async function load(){busy.value=true;try{result.value=await api.adminManagement.grading(props.offeringId);schemeName.value=result.value.scheme?.scheme_name||'Course marking scheme';items.value=(result.value.components||[]).map(x=>({...x}));if(!items.value.length) add()}catch(e){toast.error(e.message)}finally{busy.value=false}}
function add(){items.value.push({component_id:null,component_name:'',component_type:'QUIZ',weight_percentage:0,max_marks:100})}
function remove(index){if(!items.value[index].component_id)items.value.splice(index,1)}
async function save(){busy.value=true;try{await api.adminManagement.saveGrading(props.offeringId,{scheme_name:schemeName.value,components:items.value.map(x=>({component_id:x.component_id||null,component_name:x.component_name,component_type:x.component_type,weight_percentage:Number(x.weight_percentage),max_marks:Number(x.max_marks)}))});toast.success('Marking scheme saved.');emit('refresh');await load()}catch(e){toast.error(e.message)}finally{busy.value=false}}
onMounted(load)
</script>
<template>
  <SectionCard title="Assessment weights & components" subtitle="Instructors may configure schemes only for their assigned offering. Published course grades lock the scheme.">
    <div v-if="!result" class="notice notice-info">Loading assessment scheme…</div>
    <template v-else>
      <div v-if="locked" class="notice notice-warning">This scheme is locked because a final grade has been published.</div>
      <div class="field"><label>Scheme name</label><input v-model="schemeName" class="input" :disabled="locked"/></div>
      <div v-for="(c,index) in items" :key="c.component_id||`new-${index}`" class="form-grid form-grid-3" style="padding:12px 0;border-bottom:1px solid var(--border, #ddd)">
        <div class="field"><label>Assessment</label><input v-model="c.component_name" class="input" :disabled="locked"/></div>
        <div class="field"><label>Type</label><select v-model="c.component_type" class="select" :disabled="locked||Boolean(c.component_id&&c.configured==='Y')"><option v-for="t in ['ASSIGNMENT','QUIZ','EXAM','OTHER']" :key="t">{{t}}</option></select></div>
        <div class="field"><label>Weight (%)</label><input v-model.number="c.weight_percentage" class="input" type="number" min="0" max="100" step="0.01" :disabled="locked"/></div>
        <div class="field"><label>Maximum marks</label><input v-model.number="c.max_marks" class="input" type="number" min="0.01" step="0.01" :disabled="locked"/></div>
        <button v-if="!c.component_id" type="button" class="btn btn-soft btn-sm" :disabled="locked" @click="remove(index)">Remove</button>
      </div>
      <p>Total assessment weight: <strong>{{total.toFixed(2)}}%</strong> (must equal 100%)</p>
      <div style="display:flex;gap:12px;flex-wrap:wrap"><button class="btn btn-soft" :disabled="locked" @click="add">Add component</button><button class="btn btn-primary" :disabled="busy||locked||Math.abs(total-100)>0.0001||!schemeName.trim()" @click="save">{{busy?'Saving…':'Save marking scheme'}}</button></div>
    </template>
  </SectionCard>
</template>
