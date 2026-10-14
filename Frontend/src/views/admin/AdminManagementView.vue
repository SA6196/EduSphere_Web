<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppShell from '../../components/AppShell.vue'
import SectionCard from '../../components/SectionCard.vue'
import DataTable from '../../components/DataTable.vue'
import LoadingState from '../../components/LoadingState.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import { api } from '../../services/api.js'
import { toast } from '../../stores/toast.js'
import { displayLabel } from '../../utils/format.js'

const tabs = [
  { key: 'accounts', label: 'Accounts' },
  { key: 'classes', label: 'Classes & instructors' },
  { key: 'grading', label: 'Marking scheme' },
  { key: 'academic', label: 'Master data' },
  { key: 'audit', label: 'Audit & alerts' },
]
const activeTab = ref('accounts')
const academicKind=ref('course')
const academicId=ref('')
const academicForm=reactive({program_id:'',course_code:'',course_name:'',credits:3,course_description:'',department_id:'',program_name:'',program_level:'UG',semester_name:'',academic_year:'',semester_start_date:'',semester_end_date:''})
const academicBusy=ref(false)
const auditSearch=ref(''), auditBusy=ref(false), auditData=ref({logs:[],alerts:[]})
const academicFields={
  course:[['program_id','Program ID'],['course_code','Course code'],['course_name','Course name'],['credits','Credits'],['course_description','Description']],
  program:[['department_id','Department ID'],['program_name','Program name'],['program_level','Level']],
  semester:[['semester_name','Semester name'],['academic_year','Academic year'],['semester_start_date','Start date'],['semester_end_date','End date']],
}
async function saveAcademic(){
  academicBusy.value=true
  try{
    const payload=Object.fromEntries(academicFields[academicKind.value].map(([k])=>[k,academicForm[k]]))
    if(academicId.value)await api.adminManagement.masterUpdate(academicKind.value,Number(academicId.value),payload)
    else await api.adminManagement.masterCreate(academicKind.value,payload)
    toast.success('Academic master data saved.');await loadAll()
  }catch(e){toast.error(e.message)}finally{academicBusy.value=false}
}
async function loadAudit(){auditBusy.value=true;try{auditData.value=await api.adminManagement.audit(auditSearch.value)}catch(e){toast.error(e.message)}finally{auditBusy.value=false}}

const loading = ref(true)
const pending = reactive({ student:false, instructor:false, offering:false, assignment:false, grading:false })
const directory = reactive({ students:[], instructors:[], departments:[], programs:[] })
const courses = ref([])
const semesters = ref([])
const offerings = ref([])
const selectedOfferingInstructors = ref([])
const gradingState = reactive({ offering:null, scheme:null, components:[], published_grade_count:0 })
const confirm = reactive({ open:false, title:'', message:'', action:null })

const studentForm = reactive({
  username:'', password:'', email:'', phone:'', student_name:'', admission_no:'',
  batch:'', program_id:'', account_status:'ACTIVE', student_status:'ACTIVE',
})
const instructorForm = reactive({
  username:'', password:'', email:'', phone:'', instructor_name:'', designation:'',
  department_id:'', account_status:'ACTIVE',
})
const offeringForm = reactive({
  course_id:'', semester_id:'', section_code:'', slot_day:'', start_time:'', end_time:'',
  capacity:60, offering_status:'PLANNED', instructor_ids:[],
})
const assignmentForm = reactive({ offering_id:'', instructor_ids:[] })
const gradingForm = reactive({ offering_id:'', scheme_name:'' })

function rows(data){ return Array.isArray(data) ? data : (data?.results || data?.items || []) }
const activeInstructors = computed(() => directory.instructors.filter(i => i.account_status === 'ACTIVE'))
const totalWeight = computed(() => gradingState.components.reduce((sum,c) => sum + Number(c.weight_percentage || 0), 0))
const selectedGradingOffering = computed(() => offerings.value.find(o => String(o.offering_id) === String(gradingForm.offering_id)))
const gradingLocked = computed(() => Number(gradingState.published_grade_count || 0) > 0)

async function loadAll(){
  loading.value = true
  try {
    const [d, c, s, o] = await Promise.all([
      api.adminManagement.directory(), api.academics.courses(1,200),
      api.reports.semesters(), api.academics.offerings(1,200),
    ])
    Object.assign(directory, d)
    courses.value = rows(c)
    semesters.value = rows(s)
    offerings.value = rows(o)
  } catch(e) { toast.error(e.message) }
  finally { loading.value = false }
}

function resetStudent(){ Object.assign(studentForm,{username:'',password:'',email:'',phone:'',student_name:'',admission_no:'',batch:'',program_id:'',account_status:'ACTIVE',student_status:'ACTIVE'}) }
function resetInstructor(){ Object.assign(instructorForm,{username:'',password:'',email:'',phone:'',instructor_name:'',designation:'',department_id:'',account_status:'ACTIVE'}) }
function resetOffering(){ Object.assign(offeringForm,{course_id:'',semester_id:'',section_code:'',slot_day:'',start_time:'',end_time:'',capacity:60,offering_status:'PLANNED',instructor_ids:[]}) }

async function createStudent(){
  pending.student=true
  try { await api.adminManagement.createStudent({...studentForm, program_id:Number(studentForm.program_id)}); toast.success('Student account created.'); resetStudent(); await loadDirectoryOnly() }
  catch(e){ toast.error(e.message) } finally { pending.student=false }
}
async function createInstructor(){
  pending.instructor=true
  try { await api.adminManagement.createInstructor({...instructorForm, department_id:Number(instructorForm.department_id)}); toast.success('Instructor account created.'); resetInstructor(); await loadDirectoryOnly() }
  catch(e){ toast.error(e.message) } finally { pending.instructor=false }
}
async function approveStudent(row){
  if(!window.confirm(`Activate ${row.student_name} after verifying their identity?`))return
  try{await api.adminManagement.approveStudent(Number(row.student_id));toast.success('Account activated.');await loadDirectoryOnly()}
  catch(e){toast.error(e.message)}
}
async function loadDirectoryOnly(){
  const d = await api.adminManagement.directory(); Object.assign(directory,d)
}
async function createOffering(){
  pending.offering=true
  try {
    const payload={...offeringForm,course_id:Number(offeringForm.course_id),semester_id:Number(offeringForm.semester_id),capacity:Number(offeringForm.capacity),instructor_ids:offeringForm.instructor_ids.map(Number)}
    await api.adminManagement.createOffering(payload)
    toast.success('Class created and instructor assignments saved.')
    resetOffering()
    offerings.value=rows(await api.academics.offerings(1,200))
  } catch(e){ toast.error(e.message) } finally { pending.offering=false }
}
async function loadOfferingAssignments(){
  if(!assignmentForm.offering_id){ assignmentForm.instructor_ids=[]; return }
  try {
    const assigned=await api.adminManagement.offeringInstructors(Number(assignmentForm.offering_id))
    assignmentForm.instructor_ids=(assigned||[]).map(i=>Number(i.instructor_id))
    selectedOfferingInstructors.value=assigned||[]
  } catch(e){toast.error(e.message)}
}
function askSaveAssignments(){ confirm.open=true; confirm.title='Save instructor assignments?'; confirm.message='This replaces the instructor list for the selected class.'; confirm.action=saveAssignments }
async function saveAssignments(){
  confirm.open=false; pending.assignment=true
  try { selectedOfferingInstructors.value=await api.adminManagement.saveOfferingInstructors(Number(assignmentForm.offering_id),assignmentForm.instructor_ids.map(Number)); toast.success('Instructor assignments updated.') }
  catch(e){toast.error(e.message)} finally{pending.assignment=false}
}

function newComponent(){ return { component_id:null, component_name:'', component_type:'ASSIGNMENT', weight_percentage:0, max_marks:100, configured:'N' } }
async function loadGrading(){
  if(!gradingForm.offering_id) return
  pending.grading=true
  try {
    const data=await api.adminManagement.grading(Number(gradingForm.offering_id))
    gradingState.offering=data.offering
    gradingState.scheme=data.scheme
    gradingState.published_grade_count=data.published_grade_count||0
    gradingForm.scheme_name=data.scheme?.scheme_name || `${data.offering?.course_code || 'Course'} Grading Scheme`
    gradingState.components=(data.components||[]).map(c=>({...c,weight_percentage:Number(c.weight_percentage),max_marks:Number(c.max_marks)}))
    if(!gradingState.components.length) gradingState.components=[newComponent()]
  } catch(e){toast.error(e.message)} finally{pending.grading=false}
}
function addComponent(){ gradingState.components.push(newComponent()) }
function removeComponent(index){ if(gradingState.components[index]?.component_id) return; gradingState.components.splice(index,1) }
function askSaveGrading(){ confirm.open=true; confirm.title='Update marking scheme?'; confirm.message='Weights and maximum marks affect course percentages. The submitted component weights must total exactly 100%.'; confirm.action=saveGrading }
async function saveGrading(){
  confirm.open=false; pending.grading=true
  try {
    const payload={scheme_name:gradingForm.scheme_name,components:gradingState.components.map(c=>({component_id:c.component_id||null,component_name:c.component_name,component_type:c.component_type,weight_percentage:Number(c.weight_percentage),max_marks:Number(c.max_marks)}))}
    const data=await api.adminManagement.saveGrading(Number(gradingForm.offering_id),payload)
    gradingState.scheme=data.scheme; gradingState.components=(data.components||[]).map(c=>({...c,weight_percentage:Number(c.weight_percentage),max_marks:Number(c.max_marks)})); gradingState.published_grade_count=data.published_grade_count||0
    toast.success('Marking scheme updated.')
  } catch(e){toast.error(e.message)} finally{pending.grading=false}
}
function runConfirm(){ const action=confirm.action; confirm.open=false; confirm.action=null; if(action) action() }

onMounted(loadAll)
</script>

<template>
  <AppShell>
    <template #title>Admin Management</template>
    <div class="page-heading">
      <div><div class="eyebrow">Academic management</div><h1>Users, classes & marking schemes</h1><p>Create Student/Instructor accounts, open classs, assign instructors and maintain assessment weightage.</p></div>
    </div>

    <div class="management-tabs" role="tablist">
      <button v-for="tab in tabs" :key="tab.key" class="management-tab" :class="{active:activeTab===tab.key}" @click="activeTab=tab.key">{{tab.label}}</button>
    </div>

    <LoadingState v-if="loading" message="Loading administrative setup data…" />

    <template v-else-if="activeTab==='accounts'">
      <div class="grid grid-2 admin-form-grid">
        <SectionCard title="Create student account">
          <form class="stack" @submit.prevent="createStudent">
            <div class="form-grid"><div class="field"><label>Student name</label><input v-model.trim="studentForm.student_name" class="input" required /></div><div class="field"><label>Admission no</label><input v-model.trim="studentForm.admission_no" class="input" required /></div></div>
            <div class="form-grid"><div class="field"><label>Username</label><input v-model.trim="studentForm.username" class="input" required /></div><div class="field"><label>Initial password</label><input v-model="studentForm.password" class="input" type="password" minlength="6" required /></div></div>
            <div class="form-grid"><div class="field"><label>Email</label><input v-model.trim="studentForm.email" class="input" type="email" required /></div><div class="field"><label>Phone</label><input v-model.trim="studentForm.phone" class="input" /></div></div>
            <div class="form-grid"><div class="field"><label>Program</label><select v-model="studentForm.program_id" class="select" required><option value="" disabled>Select program</option><option v-for="p in directory.programs" :key="p.program_id" :value="p.program_id">{{p.program_name}} · {{p.program_level}} · {{p.department_name}}</option></select></div><div class="field"><label>Batch</label><input v-model.trim="studentForm.batch" class="input" placeholder="2026" /></div></div>
            <button class="btn btn-primary" type="submit" :disabled="pending.student">{{pending.student?'Creating…':'Create student account'}}</button>
          </form>
        </SectionCard>

        <SectionCard title="Create instructor account">
          <form class="stack" @submit.prevent="createInstructor">
            <div class="form-grid"><div class="field"><label>Instructor name</label><input v-model.trim="instructorForm.instructor_name" class="input" required /></div><div class="field"><label>Designation</label><input v-model.trim="instructorForm.designation" class="input" placeholder="Assistant Professor" /></div></div>
            <div class="form-grid"><div class="field"><label>Username</label><input v-model.trim="instructorForm.username" class="input" required /></div><div class="field"><label>Initial password</label><input v-model="instructorForm.password" class="input" type="password" minlength="6" required /></div></div>
            <div class="form-grid"><div class="field"><label>Email</label><input v-model.trim="instructorForm.email" class="input" type="email" required /></div><div class="field"><label>Phone</label><input v-model.trim="instructorForm.phone" class="input" /></div></div>
            <div class="field"><label>Department</label><select v-model="instructorForm.department_id" class="select" required><option value="" disabled>Select department</option><option v-for="d in directory.departments" :key="d.department_id" :value="d.department_id">{{d.department_name}}</option></select></div>
            <button class="btn btn-primary" type="submit" :disabled="pending.instructor">{{pending.instructor?'Creating…':'Create instructor account'}}</button>
          </form>
        </SectionCard>
      </div>

      <SectionCard title="Students"><DataTable :rows="directory.students" :columns="[{key:'admission_no',label:'Admission no'},{key:'student_name',label:'Student'},{key:'program_name',label:'Program'},{key:'batch',label:'Batch'},{key:'username',label:'Username'},{key:'account_status',label:'Account'},{key:'student_status',label:'Student status'}]"><template #cell-account_status="{value}"><StatusBadge :value="value" /></template><template #cell-student_status="{value}"><StatusBadge :value="value" /></template><template #actions="{row}"><button v-if="row.account_status==='INACTIVE'" class="btn btn-primary btn-sm" @click="approveStudent(row)">Approve after verification</button></template></DataTable></SectionCard>
      <SectionCard title="Instructors"><DataTable :rows="directory.instructors" :columns="[{key:'instructor_name',label:'Instructor'},{key:'department_name',label:'Department'},{key:'designation',label:'Designation'},{key:'username',label:'Username'},{key:'account_status',label:'Account'}]"><template #cell-account_status="{value}"><StatusBadge :value="value" /></template></DataTable></SectionCard>
    </template>

    <template v-else-if="activeTab==='classes'">
      <SectionCard title="Create class">
        <form class="stack" @submit.prevent="createOffering">
          <div class="form-grid form-grid-3"><div class="field"><label>Course</label><select v-model="offeringForm.course_id" class="select" required><option value="" disabled>Select course</option><option v-for="c in courses" :key="c.course_id" :value="c.course_id">{{c.course_code}} · {{c.course_name}}</option></select></div><div class="field"><label>Semester</label><select v-model="offeringForm.semester_id" class="select" required><option value="" disabled>Select semester</option><option v-for="s in semesters" :key="s.semester_id" :value="s.semester_id">{{s.semester_name}} · {{s.academic_year}}</option></select></div><div class="field"><label>Section</label><input v-model.trim="offeringForm.section_code" class="input" required placeholder="A" /></div></div>
          <div class="form-grid form-grid-3"><div class="field"><label>Day</label><select v-model="offeringForm.slot_day" class="select"><option value="">No fixed day</option><option v-for="d in ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY']" :key="d" :value="d">{{displayLabel(d)}}</option></select></div><div class="field"><label>Start time</label><input v-model="offeringForm.start_time" class="input" type="time" /></div><div class="field"><label>End time</label><input v-model="offeringForm.end_time" class="input" type="time" /></div></div>
          <div class="form-grid"><div class="field"><label>Capacity</label><input v-model.number="offeringForm.capacity" class="input" type="number" min="1" required /></div><div class="field"><label>Initial status</label><select v-model="offeringForm.offering_status" class="select"><option value="PLANNED">{{displayLabel('PLANNED')}}</option><option value="OPEN">{{displayLabel('OPEN')}}</option></select></div></div>
          <div class="field"><label>Assign instructors now</label><div class="check-grid"><label v-for="i in activeInstructors" :key="i.instructor_id" class="check-card"><input v-model="offeringForm.instructor_ids" type="checkbox" :value="i.instructor_id" /><span><strong>{{i.instructor_name}}</strong><small>{{i.department_name}} · {{i.designation||'Instructor'}}</small></span></label></div></div>
          <button class="btn btn-primary" type="submit" :disabled="pending.offering">{{pending.offering?'Creating…':'Create class'}}</button>
        </form>
      </SectionCard>

      <SectionCard title="Assign instructors to an existing class">
        <div class="field"><label>Class</label><select v-model="assignmentForm.offering_id" class="select" @change="loadOfferingAssignments"><option value="">Select class</option><option v-for="o in offerings" :key="o.offering_id" :value="o.offering_id">{{o.course_code}} · {{o.course_name}} · Section {{o.section_code}} · {{displayLabel(o.offering_status)}}</option></select></div>
        <div v-if="assignmentForm.offering_id" class="stack" style="margin-top:14px"><div class="check-grid"><label v-for="i in activeInstructors" :key="i.instructor_id" class="check-card"><input v-model="assignmentForm.instructor_ids" type="checkbox" :value="i.instructor_id" /><span><strong>{{i.instructor_name}}</strong><small>{{i.department_name}} · {{i.designation||'Instructor'}}</small></span></label></div><button class="btn btn-primary" :disabled="pending.assignment" @click="askSaveAssignments">{{pending.assignment?'Saving…':'Save instructor assignments'}}</button></div>
      </SectionCard>
    </template>

    <template v-else-if="activeTab==='grading'">
      <SectionCard title="Edit marking scheme & weightage">
        <div class="form-grid"><div class="field"><label>Class</label><select v-model="gradingForm.offering_id" class="select"><option value="">Select class</option><option v-for="o in offerings" :key="o.offering_id" :value="o.offering_id">{{o.course_code}} · {{o.course_name}} · Section {{o.section_code}} · {{displayLabel(o.offering_status)}}</option></select></div><div class="field" style="align-self:end"><button class="btn btn-primary" :disabled="!gradingForm.offering_id||pending.grading" @click="loadGrading">{{pending.grading?'Loading…':'Load marking scheme'}}</button></div></div>
      </SectionCard>

      <template v-if="gradingState.offering">
        <div v-if="gradingLocked" class="notice notice-error">This marking scheme is locked because {{gradingState.published_grade_count}} final course grade(s) have already been published for this class.</div>
        <SectionCard :title="`${selectedGradingOffering?.course_code || gradingState.offering.course_code} marking scheme`">
          <div class="field"><label>Scheme name</label><input v-model.trim="gradingForm.scheme_name" class="input" :disabled="gradingLocked" /></div>
          <div class="component-editor-head"><strong>Assessments</strong><div class="weight-total" :class="{valid:Math.abs(totalWeight-100)<0.001,invalid:Math.abs(totalWeight-100)>=0.001}">Total weight: {{totalWeight.toFixed(2)}}%</div></div>
          <div class="component-editor">
            <div v-for="(c,index) in gradingState.components" :key="c.component_id || `new-${index}`" class="component-row">
              <div class="field"><label>Component name</label><input v-model.trim="c.component_name" class="input" :disabled="gradingLocked" /></div>
              <div class="field"><label>Type</label><select v-model="c.component_type" class="select" :disabled="gradingLocked || (c.component_id && c.configured==='Y')"><option value="ASSIGNMENT">{{displayLabel('ASSIGNMENT')}}</option><option value="QUIZ">{{displayLabel('QUIZ')}}</option><option value="EXAM">{{displayLabel('EXAM')}}</option><option value="OTHER">{{displayLabel('OTHER')}}</option></select></div>
              <div class="field"><label>Weight %</label><input v-model.number="c.weight_percentage" class="input" type="number" min="0" max="100" step="0.01" :disabled="gradingLocked" /></div>
              <div class="field"><label>Max marks</label><input v-model.number="c.max_marks" class="input" type="number" min="0.01" step="0.01" :disabled="gradingLocked" /></div>
              <div class="component-row-action"><StatusBadge v-if="c.configured==='Y'" value="Configured" /><button v-else-if="!c.component_id" class="btn btn-soft btn-sm" type="button" :disabled="gradingLocked" @click="removeComponent(index)">Remove</button></div>
            </div>
          </div>
          <div class="editor-actions"><button class="btn btn-soft" type="button" :disabled="gradingLocked" @click="addComponent">Add component</button><button class="btn btn-primary" type="button" :disabled="gradingLocked || pending.grading || Math.abs(totalWeight-100)>=0.001 || !gradingForm.scheme_name" @click="askSaveGrading">{{pending.grading?'Saving…':'Save marking scheme'}}</button></div>
        </SectionCard>
      </template>
    </template>

    <template v-else-if="activeTab==='academic'">
      <SectionCard title="Program, course & semester management" subtitle="Create or update existing records without changing the 37-table schema. Leave Record ID blank to create a new record.">
        <form class="form-grid form-grid-3" @submit.prevent="saveAcademic">
          <div class="field"><label>Record type</label><select v-model="academicKind" class="select"><option value="program">Program</option><option value="course">Course</option><option value="semester">Semester</option></select></div>
          <div class="field"><label>Existing record ID (optional)</label><input v-model="academicId" class="input" type="number" min="1" placeholder="Blank = create" /></div>
          <div v-for="[field,label] in academicFields[academicKind]" :key="field" class="field"><label>{{label}}</label><input v-model="academicForm[field]" class="input" :type="field.endsWith('_date')?'date':(['credits','program_id','department_id'].includes(field)?'number':'text')" :step="field==='credits'?'0.1':undefined" :required="!academicId"/></div>
          <div class="field" style="align-self:end"><button class="btn btn-primary" :disabled="academicBusy" type="submit">{{academicBusy?'Saving…':(academicId?'Update record':'Create record')}}</button></div>
        </form>
      </SectionCard>
      <SectionCard title="Existing programs"><DataTable :rows="directory.programs" :columns="[{key:'program_id',label:'ID'},{key:'program_name',label:'Program'},{key:'program_level',label:'Level'},{key:'department_name',label:'Department'}]"/></SectionCard>
      <SectionCard title="Existing courses"><DataTable :rows="courses" :columns="[{key:'course_id',label:'ID'},{key:'course_code',label:'Course'},{key:'course_name',label:'Name'},{key:'credits',label:'Credits'}]"/></SectionCard>
      <SectionCard title="Existing semesters"><DataTable :rows="semesters" :columns="[{key:'semester_id',label:'ID'},{key:'semester_name',label:'Semester'},{key:'academic_year',label:'Year'}]"/></SectionCard>
    </template>

    <template v-else-if="activeTab==='audit'">
      <SectionCard title="Audit log & system alerts" subtitle="Administrator-only read-only monitoring of ACTIVITY_LOG and grading exceptions.">
        <form class="form-grid" @submit.prevent="loadAudit"><div class="field"><label>Search activity</label><input v-model="auditSearch" class="input" placeholder="Activity type or description"/></div><div class="field" style="align-self:end"><button class="btn btn-primary" :disabled="auditBusy" type="submit">{{auditBusy?'Loading…':'Refresh audit'}}</button></div></form>
        <DataTable :rows="auditData.alerts||[]" :columns="[{key:'kind',label:'Alert'},{key:'quiz_id',label:'Quiz ID'},{key:'attempt_id',label:'Attempt ID'}]" empty="No grading exceptions detected." />
        <DataTable :rows="auditData.logs||[]" :columns="[{key:'activity_date_time',label:'Date'},{key:'username',label:'User'},{key:'activity_type',label:'Event'},{key:'activity_description',label:'Details'}]" empty="Select Refresh audit to view activity." />
      </SectionCard>
    </template>

    <ConfirmDialog :open="confirm.open" :title="confirm.title" :message="confirm.message" confirm-label="Confirm" @cancel="confirm.open=false" @confirm="runConfirm" />
  </AppShell>
</template>
