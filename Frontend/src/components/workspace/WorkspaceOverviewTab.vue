<script setup>
import SectionCard from '../SectionCard.vue'
import DataTable from '../DataTable.vue'
import StatusBadge from '../StatusBadge.vue'
import EmptyState from '../EmptyState.vue'
defineProps({ offering:Object, grading:Object, components:{type:Array,default:()=>[]} })
</script>
<template>
  <div class="grid grid-2">
    <SectionCard title="Class information">
      <div class="grid grid-2">
        <div class="field"><label>Course</label><div>{{ offering.course_code }} — {{ offering.course_name }}</div></div>
        <div class="field"><label>Section</label><div>{{ offering.section_code }}</div></div>
        <div class="field"><label>Capacity</label><div>{{ offering.capacity }}</div></div>
        <div class="field"><label>Status</label><StatusBadge :value="offering.offering_status" /></div>
      </div>
    </SectionCard>
    <SectionCard title="Grading scheme">
      <div v-if="grading?.grading_scheme"><strong>{{ grading.grading_scheme.scheme_name }}</strong><div class="course-meta">{{ grading.component_count }} assessment(s)</div></div>
      <EmptyState v-else title="No grading scheme" message="No grading scheme is configured for this class." />
    </SectionCard>
  </div>
  <SectionCard title="Assessments" subtitle="Assignments, quizzes and exams are linked automatically through their assessments.">
    <DataTable :rows="components" :columns="[
      {key:'component_name',label:'Component'}, {key:'component_type',label:'Assessment type'}, {key:'weight_percentage',label:'Weight %'}, {key:'max_marks',label:'Max marks'}, {key:'configured',label:'Available'}
    ]">
      <template #cell-component_type="{ value }"><StatusBadge :value="value" /></template>
      <template #cell-configured="{ value }"><StatusBadge :value="value" /></template>
    </DataTable>
  </SectionCard>
</template>
