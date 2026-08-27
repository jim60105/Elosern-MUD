<script setup>
// SkillBook (B3 data family): the character's skill data as a two-level
// book — active/passive tabs, a bounded search, and the payload's own
// category → group → skill ordering (never re-sorted). The character
// presenter now enriches every registry-resolvable active skill row with
// cost, target_spec, usable_out_of_combat, and (for a freeform-eligible
// skill the actor has mastery to scale) freeform_scales; a row the payload
// gives without detail (e.g. an unregistered-key fallback row) renders
// without detail cells, so nothing is invented. Tab and search are view-local
// UI state.
import { ref, computed } from "vue";

const props = defineProps({
  // The character's skill data: { actives, passives } in the character
  // payload's category/`groups`/`{key,label}` shape, with optional
  // skill-descriptor detail fields on individual rows.
  skills: { type: Object, required: true },
  // Showcase/mount convenience: the tab selected on first render.
  initialTab: { type: String, default: "active" },
  // Showcase/mount convenience: the search string on first render.
  initialQuery: { type: String, default: "" },
});

const TARGET_LABELS = {
  none: "無目標",
  self: "自身",
  single: "單一目標",
  area: "範圍",
};

const tab = ref(
  props.initialTab === "passive" ? "passive" : "active",
);
const query = ref(props.initialQuery);

function skillCount(rows) {
  let count = 0;
  for (const category of rows ?? []) {
    for (const group of category.groups ?? []) {
      count += (group.skills ?? []).length;
    }
  }
  return count;
}

// The active/passive totals now render in the drawer head (`HudDrawer`'s
// subtitle, computed in `AppClient`); the book itself no longer shows them.

function matches(row, group, category) {
  const q = query.value.trim().toLowerCase();
  if (!q) return true;
  return [row.label, group?.label, category?.label].some(
    (label) => typeof label === "string" && label.toLowerCase().includes(q),
  );
}

function filterCategories(rows) {
  const filtered = [];
  for (const category of rows ?? []) {
    const groups = [];
    for (const group of category.groups ?? []) {
      const skills = (group.skills ?? []).filter((row) =>
        matches(row, group, category),
      );
      if (skills.length > 0) {
        groups.push({ ...group, skills });
      }
    }
    if (groups.length > 0) {
      filtered.push({ ...category, groups });
    }
  }
  return filtered;
}

const visibleCategories = computed(() =>
  tab.value === "active"
    ? filterCategories(props.skills?.actives)
    : filterCategories(props.skills?.passives),
);

const visibleTotal = computed(() =>
  skillCount(visibleCategories.value),
);

// Cost cell: the descriptor's `cost` is a bounded object and the empty
// object is its free form, so {} renders the honest 免費; a non-empty object
// lists only the resources it actually spends; a row without a cost field at
// all renders no cost cell.
function costText(row) {
  if (!("cost" in row)) return null;
  const cost = row.cost ?? {};
  const parts = [];
  if (cost.mp) parts.push(`${cost.mp} mp`);
  if (cost.sp) parts.push(`${cost.sp} sp`);
  return parts.length > 0 ? parts.join(" ・ ") : "免費";
}

function targetText(row) {
  if (!row.target_spec) return null;
  return TARGET_LABELS[row.target_spec] ?? row.target_spec;
}

// Cast cell: power scales (with their per-scale mp costs) and the target
// shorthands the descriptor allows at cast time.
function castText(row) {
  const parts = [];
  if (Array.isArray(row.freeform_scales) && row.freeform_scales.length > 0) {
    parts.push(
      `威力 ${row.freeform_scales
        .map((s) => `${s.label}（${s.mp_cost} mp）`)
        .join("・")}`,
    );
  }
  if (Array.isArray(row.shorthands) && row.shorthands.length > 0) {
    parts.push(`範圍代號 ${row.shorthands.join("／")}`);
  }
  return parts.length > 0 ? parts.join("；") : null;
}
</script>

<template>
  <section class="skill-book" data-testid="skill-book">
    <!-- The book's title and active/passive counts now render once, in the
         drawer head (`HudDrawer`'s `title` + `subtitle`), not here. -->
    <div class="skill-book__tabs" role="tablist" data-testid="skill-book__tabs">
      <button
        type="button"
        role="tab"
        class="skill-book__tab"
        :class="{ on: tab === 'active' }"
        :aria-selected="String(tab === 'active')"
        data-testid="skill-book__tab--active"
        @click="tab = 'active'"
      >
        主動
      </button>
      <button
        type="button"
        role="tab"
        class="skill-book__tab"
        :class="{ on: tab === 'passive' }"
        :aria-selected="String(tab === 'passive')"
        data-testid="skill-book__tab--passive"
        @click="tab = 'passive'"
      >
        被動
      </button>
    </div>

    <!-- The search field reads as one single-bordered control with a leading
         magnifying-glass icon (the reference's `.searchbox`): the icon +
         input share one bordered wrapper; the input itself is borderless. -->
    <div class="skill-book__search-wrap">
      <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <circle cx="11" cy="11" r="6"></circle>
        <path d="M20 20l-4-4" stroke-linecap="round"></path>
      </svg>
      <input
        v-model="query"
        class="skill-book__search"
        type="search"
        placeholder="搜尋技能（例：火 / 治癒 / 逃跑）"
        data-testid="skill-book__search"
      />
    </div>

    <p
      v-if="visibleTotal === 0"
      class="skill-book__empty"
      data-testid="skill-book__empty"
    >
      沒有符合的技能
    </p>

    <details
      v-for="(category, index) in visibleCategories"
      :key="category.category"
      class="skill-book__category"
      data-testid="skill-book__category"
      :data-category="category.category"
      :open="index === 0"
    >
      <summary class="skill-book__category-summary">
        <span class="skill-book__category-label">{{ category.label }}</span>
      </summary>
      <div
        v-for="group in category.groups"
        :key="group.group ?? `${category.category}-ungrouped`"
        class="skill-book__group"
        :data-testid="`skill-book__group--${group.group ?? 'ungrouped'}`"
        :data-group="group.group ?? ''"
      >
        <p
          v-if="group.label"
          class="skill-book__group-label"
          data-testid="skill-book__group-label"
        >
          {{ group.label }}
        </p>
        <div
          v-for="row in group.skills"
          :key="row.key"
          class="skill-book__skill"
          data-testid="skill-book__skill"
          :data-key="row.key"
        >
          <span class="skill-book__skill-name">{{ row.label }}</span>
          <span
            v-if="row.usable_out_of_combat === true"
            class="skill-book__ooc"
            data-testid="skill-book__ooc"
          >
            combat
          </span>
          <span
            v-if="costText(row) !== null"
            class="skill-book__cost"
            data-testid="skill-book__cost"
          >
            {{ costText(row) }}
          </span>
          <span
            v-if="targetText(row) !== null"
            class="skill-book__target"
            data-testid="skill-book__target"
          >
            {{ targetText(row) }}
          </span>
          <span
            v-if="castText(row) !== null"
            class="skill-book__cast"
            data-testid="skill-book__cast"
          >
            {{ castText(row) }}
          </span>
        </div>
      </div>
    </details>
  </section>
</template>

<style scoped>
.skill-book {
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

/* The 主動/被動 pair: a full-width, evenly-split segmented control (each
   tab takes `flex: 1`, centered text), matching the reference's two-up tab
   pair that spans the drawer width. */
.skill-book__tabs {
  display: flex;
  gap: var(--sp-1);
  width: 100%;
}

.skill-book__tab {
  flex: 1;
  padding: 4px var(--sp-3);
  text-align: center;
  color: var(--paper-500);
  background: none;
  border: var(--line);
  border-radius: var(--radius-sm);
  font-size: 0.85em;
  cursor: pointer;
}

.skill-book__tab.on {
  color: var(--paper-50);
  border-color: var(--seal-600);
}

/* One single-bordered control (the reference's `.searchbox`): the wrapper
   carries the border/background; the input is borderless and flex-grows. */
.skill-book__search-wrap {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 12px;
  background: var(--ink-820);
  border: 1px solid var(--ink-600);
  border-radius: 9px;
}

.skill-book__search-wrap svg {
  flex: none;
  color: var(--paper-500);
}

/* Keyboard focus: the borderless input shows no ring of its own
   (`outline: none`), so the wrapper carries the shared `--focus` shadow
   token when the input holds focus — a visible focus indicator for
   keyboard users. */
.skill-book__search-wrap:focus-within {
  border-color: var(--gold-500);
  box-shadow: var(--focus);
}

.skill-book__search {
  flex: 1;
  min-width: 0;
  color: var(--paper-50);
  background: transparent;
  border: 0;
  outline: none;
  font-size: 13px;
  font-family: var(--f-sans);
}

.skill-book__empty {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
}

.skill-book__category {
  border-top: var(--line);
  padding-top: var(--sp-2);
}

.skill-book__category-summary {
  cursor: pointer;
  color: var(--paper-100);
  font-size: 0.9em;
}

.skill-book__group {
  margin-top: var(--sp-2);
}

.skill-book__group-label {
  margin: 0 0 var(--sp-1);
  color: var(--warn);
  font-size: 0.8em;
}

.skill-book__skill {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-2);
  padding: 1px 0;
  font-size: 0.9em;
}

.skill-book__skill-name {
  color: var(--paper-100);
}

.skill-book__cost,
.skill-book__target,
.skill-book__cast {
  color: var(--paper-500);
  font-family: var(--f-mono);
  font-size: 0.85em;
}

.skill-book__ooc {
  color: var(--paper-500);
  border: var(--line);
  border-radius: 999px;
  padding: 0 var(--sp-1);
  font-family: var(--f-mono);
  font-size: 0.75em;
}
</style>
