<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Resource URL' },
  placeholder: { type: String, default: 'https://…' },
  required: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <div class="field full">
    <label>{{ label }}</label>
    <input
      :value="modelValue"
      class="input"
      type="url"
      :placeholder="placeholder"
      :required="required"
      autocomplete="url"
      @input="emit('update:modelValue', $event.target.value)"
    />
    <div class="help strong-help">Enter a hosted or shared URL. The current EduSphere backend stores resource links rather than uploading local file bytes.</div>
  </div>
</template>
