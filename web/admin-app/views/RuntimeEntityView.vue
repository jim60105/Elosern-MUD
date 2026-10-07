<script setup>
// The runtime entity page route wrapper: the route owns the identity, the
// entity shell owns the presentation. Keeping them separate means the shell
// is a plain component (story-able) and the route is one thin mapping.
import { computed, inject } from "vue";
import { useRoute } from "vue-router";
import GmEntityView from "../components/GmEntityView.vue";

const api = inject("gmApi");
const route = useRoute();
const kind = computed(() => String(route.params.kind ?? ""));
const id = computed(() => String(route.params.id ?? ""));
const owner = computed(() => (route.query.owner ? String(route.query.owner) : ""));
</script>

<template>
  <GmEntityView
    :key="`${kind}/${id}/${owner}`"
    :kind="kind"
    :id="id"
    :owner="owner"
    :api="api"
  />
</template>
