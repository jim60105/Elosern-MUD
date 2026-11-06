<script setup>
// Read-only monster spawn facts below the generic inspector header: the stale
// notice, then one block per composition (its chance for a zone) with one row
// per member. No controls and no emits: spawn data is edited through git.
// Authored text renders through text interpolation only.
defineProps({
  detail: { type: Object, required: true },
  notice: { type: String, default: "" },
});
</script>

<template>
  <div class="monster-inspector">
    <p v-if="notice" class="inspector__reason" data-monster-stale>{{ notice }}</p>
    <h3 class="section-label">生成內容</h3>
    <section
      v-for="composition in detail.compositions"
      :key="composition.key"
      class="monster-inspector__composition"
      data-monster-composition
    >
      <p class="monster-inspector__head">
        <span class="mono">{{ composition.key }}</span>
        <span v-if="composition.chance !== null" class="tag">{{ composition.chance }}</span>
      </p>
      <p v-for="(member, index) in composition.members" :key="index" data-monster-member>
        {{ member.species }} · {{ member.variant }} × {{ member.count }}
      </p>
    </section>
  </div>
</template>
