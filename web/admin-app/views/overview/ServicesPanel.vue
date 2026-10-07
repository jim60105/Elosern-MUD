<script setup>
// 服務狀態: four status cards. Each card maps its own slot, so one failing
// service source never hides the other three; an offline service is a
// critical card, never an error page.
import { computed } from "vue";
import GmPanel from "../../components/GmPanel.vue";
import GmServiceCard from "../../components/GmServiceCard.vue";
import { backendCard, llmCard, sdCard } from "../../lib/dashboard.js";

const props = defineProps({
  services: { type: Object, default: null },
  now: { type: Number, required: true },
});

const cards = computed(() => {
  const services = props.services;
  if (!services) return null;
  return [
    { key: "sd", ...sdCard(services.sd, props.now) },
    { key: "translate", ...backendCard("翻譯", services.translate, props.now) },
    { key: "cutout", ...backendCard("去背", services.cutout, props.now) },
    { key: "llm", ...llmCard(services.llm) },
  ];
});
</script>

<template>
  <GmPanel title="服務狀態" description="外部服務與後端設定；離線服務不影響總覽其他區塊">
    <div v-if="cards" class="gm-services" data-testid="gm-services">
      <GmServiceCard
        v-for="card in cards"
        :key="card.key"
        :data-service="card.key"
        :name="card.name"
        :status="card.status"
        :status-label="card.statusLabel"
        :detail="card.detail"
        :meta="card.meta"
        :error="card.error"
      />
    </div>
    <div v-else class="gm-services" aria-hidden="true">
      <div v-for="index in 4" :key="index" class="gm-services__ghost">
        <span class="gm-skeleton" style="width: 40%"></span>
        <span class="gm-skeleton" style="width: 70%"></span>
        <span class="gm-skeleton" style="width: 55%"></span>
      </div>
    </div>
  </GmPanel>
</template>

<style scoped>
.gm-services {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-4);
}

.gm-services__ghost {
  display: grid;
  gap: var(--sp-3);
  min-height: 132px;
  padding: var(--sp-4);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

@container gm-dashboard (max-width: 1099px) {
  .gm-services {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@container gm-dashboard (max-width: 759px) {
  .gm-services {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
