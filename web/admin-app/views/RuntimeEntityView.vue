<script setup>
// The runtime entity page route wrapper: the route owns the identity, the
// entity shell owns the presentation. Keeping them separate means the shell
// is a plain component (story-able) and the route is one thin mapping.
import { computed, inject } from "vue";
import { useRoute } from "vue-router";
import GmEntityView from "../components/GmEntityView.vue";

const api = inject("gmApi");
const route = useRoute();
// The reserved raw route names its parameter in the dbref namespace, so it is
// mapped explicitly instead of being read as a kind/id pair.
const isRawRoute = computed(() => route.name === "runtime-object-raw");
const kind = computed(() =>
  isRawRoute.value ? "object" : String(route.params.kind ?? ""),
);
const id = computed(() =>
  isRawRoute.value ? String(route.params.dbref ?? "") : String(route.params.id ?? ""),
);
const owner = computed(() => (route.query.owner ? String(route.query.owner) : ""));
const tab = computed(() => (route.query.tab ? String(route.query.tab) : ""));
</script>

<template>
  <GmEntityView
    :key="`${kind}/${id}/${owner}/${tab}`"
    :kind="kind"
    :id="id"
    :owner="owner"
    :tab="tab"
    :api="api"
  />
</template>
