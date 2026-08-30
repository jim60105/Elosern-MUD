<script setup>
// TitleBallotMenu (title-epithet-nomination): the pending 異名提名 ballot
// surface over the committed `title_ballot` v1 panel. Design D4: the surface
// is a host, not a data source — it renders only the server-authored
// candidates (the numbered choice 「index. display」 with its basis quote)
// and invents nothing. Each 接受 N button emits exactly one
// `title.accept` {index} intent and 放棄 one `title.decline` {} intent to
// the parent, which owns the single store dispatch (the shop/quest precedent).
//
// Zero candidates — the idle panel, the unavailable form, or no panel at all
// — renders NOTHING: the menu is an offer, never an empty shell. Basis text
// is server-authored within its storage cap (world.rules.titles bounds), so
// this component never truncates; answering through the telnet `title`
// command or a reconnect re-renders the panel truthfully from canonical
// state.
import { computed } from "vue";

const props = defineProps({
  // The committed `title_ballot` v1 panel payload (null when absent).
  ballot: { type: Object, default: null },
});

const emit = defineEmits(["accept", "decline"]);

const candidates = computed(() => {
  const panel = props.ballot;
  if (!panel || panel.available !== true || !Array.isArray(panel.candidates)) {
    return [];
  }
  return panel.candidates;
});

function acceptVote(candidate) {
  emit("accept", {
    action_id: "title.accept",
    payload: { index: candidate.index },
  });
}

function declineBallot() {
  emit("decline", { action_id: "title.decline", payload: {} });
}
</script>

<template>
  <section
    v-if="candidates.length > 0"
    class="title-ballot"
    aria-label="異名提名"
    data-testid="title-ballot-menu"
  >
    <h3 class="title-ballot__title" data-testid="title-ballot-menu__title">
      異名提名（待決）
    </h3>
    <ul class="title-ballot__list">
      <li
        v-for="candidate in candidates"
        :key="candidate.index"
        class="title-ballot__candidate"
        :data-testid="`title-ballot-menu__candidate--${candidate.index}`"
      >
        <div class="title-ballot__head">
          <span class="title-ballot__choice">{{ candidate.index }}. {{ candidate.display }}</span>
          <button
            type="button"
            class="title-ballot__accept"
            :data-testid="`title-ballot-menu__accept--${candidate.index}`"
            @click="acceptVote(candidate)"
          >
            接受 {{ candidate.index }}
          </button>
        </div>
        <p class="title-ballot__basis" data-testid="title-ballot-menu__basis">
          「{{ candidate.basis }}」
        </p>
      </li>
    </ul>
    <button
      type="button"
      class="title-ballot__decline"
      data-testid="title-ballot-menu__decline"
      @click="declineBallot"
    >
      放棄
    </button>
  </section>
</template>

<style scoped>
.title-ballot {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  box-sizing: border-box;
  padding: var(--sp-3) var(--sp-4);
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  font-family: var(--f-sans);
}

.title-ballot__title {
  margin: 0;
  color: var(--seal-400);
  font-family: var(--f-display);
  font-size: 0.95em;
}

.title-ballot__list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.title-ballot__candidate {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2);
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-hi);
}

.title-ballot__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-2);
}

.title-ballot__choice {
  color: var(--paper-50);
  font-family: var(--f-display);
}

.title-ballot__basis {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.title-ballot__accept {
  align-self: auto;
  padding: 2px var(--sp-2);
  color: var(--paper-50);
  background: transparent;
  border: 1px solid var(--seal-600);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.85em;
  cursor: pointer;
}

.title-ballot__accept:hover {
  background: var(--seal-600);
}

.title-ballot__decline {
  align-self: flex-start;
  padding: 2px var(--sp-2);
  color: var(--paper-500);
  background: transparent;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.85em;
  cursor: pointer;
}
</style>
