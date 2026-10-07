<script setup>
defineProps({ result: { type: Object, default: null }, error: { type: Object, default: null } });
</script>
<template>
  <div v-if="result || error" :role="error ? 'alert' : 'status'" class="gm-console-result">
    <p v-if="error">{{ error.code }} · {{ error.message }}</p>
    <p v-else>操作已完成。</p>
    <p v-if="(error?.snapshot ?? result?.snapshot)?.taken" class="gm-mono">介入前存檔 {{ (error?.snapshot ?? result?.snapshot).save_id }}</p>
    <p v-else>本次未建立介入前存檔。</p>
    <p v-if="result?.state?.error">{{ result.state.error.code }} · {{ result.state.error.message }}</p>
  </div>
</template>
<style scoped>
.gm-console-result { padding: var(--sp-3); border: var(--line); color: var(--paper-200); }
</style>
