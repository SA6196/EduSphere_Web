<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../services/api.js'
const programs=ref([]), error=ref(''),success=ref(''), busy=ref(false)
const form=reactive({username:'',password:'',email:'',student_name:'',admission_no:'',program_id:'',phone:'',batch:''})
onMounted(async()=>{try{programs.value=await api.registration.programs()}catch(e){error.value=e.message}})
async function submit(){busy.value=true;error.value='';try{const result=await api.registration.signup({...form,program_id:Number(form.program_id)});success.value=result.message}catch(e){error.value=e.message}finally{busy.value=false}}
</script>
<template>
  <div class="login-page"><section class="login-hero"><div class="login-brand">EduSphere LMS</div><div class="login-copy"><h1>Student registration</h1><p>Registration requests require administrative identity verification before you can sign in. Do not register on behalf of another student.</p></div></section>
    <section class="login-form-side"><form class="login-form" @submit.prevent="submit"><h2>Apply for an account</h2><div v-if="error" class="notice notice-error">{{error}}</div><div v-if="success" class="notice notice-info">{{success}}</div>
      <div class="field"><label>Student name</label><input v-model="form.student_name" class="input" required maxlength="120" /></div>
      <div class="field"><label>Admission / registration number</label><input v-model="form.admission_no" class="input" required maxlength="30" /></div>
      <div class="field"><label>Program</label><select v-model="form.program_id" class="select" required><option value="" disabled>Choose program</option><option v-for="p in programs" :key="p.program_id" :value="p.program_id">{{p.program_name}} · {{p.program_level}}</option></select></div>
      <div class="field"><label>Username</label><input v-model="form.username" class="input" autocomplete="username" required minlength="4" maxlength="50" /></div>
      <div class="field"><label>Email</label><input v-model="form.email" class="input" type="email" required /></div>
      <div class="field"><label>Password</label><input v-model="form.password" class="input" type="password" minlength="10" maxlength="128" autocomplete="new-password" required /></div>
      <button class="btn btn-primary btn-full" :disabled="busy||Boolean(success)" type="submit">{{busy?'Submitting…':'Submit registration request'}}</button>
      <RouterLink class="btn btn-soft" to="/login">Return to sign in</RouterLink>
    </form></section>
  </div>
</template>
