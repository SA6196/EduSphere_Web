<script setup>
import SectionCard from '../SectionCard.vue'
import DataTable from '../DataTable.vue'
import StatusBadge from '../StatusBadge.vue'
defineProps({attendance:{type:Array,default:()=>[]}})
</script>
<template><SectionCard title="My attendance for this class"><DataTable :rows="attendance" :columns="[{key:'session_date',label:'Date'},{key:'start_time',label:'Start'},{key:'end_time',label:'End'},{key:'session_type',label:'Session type'},{key:'topic',label:'Topic'},{key:'attendance_status',label:'Status'},{key:'remarks',label:'Remarks'}]"><template #cell-session_type="{value}"><StatusBadge :value="value" /></template><template #cell-attendance_status="{value}"><StatusBadge :value="value" /></template></DataTable></SectionCard></template>
