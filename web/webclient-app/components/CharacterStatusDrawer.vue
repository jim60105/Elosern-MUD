<script setup>
// CharacterStatusDrawer (H4, webclient-hud-04-reference-drawers, task 5.3):
// the 角色狀態 drawer body. It presents the committed `status` v1 payload's
// vitals (hp/mp/sp gauges) and the FULL condition roster (no 6-chip cap,
// unlike H2's ConditionChips island), plus the `character` v5 payload body
// (traits, disguise, guild, persona, intimate). In every mode the status
// sections render; when the `character` panel is unavailable the drawer
// shows the registry-owned reason and invents nothing. The equipment doll
// and the single drawer-layer wallet now live in the inventory drawer
// (relocate-inventory-drawer-essentials). The 親密狀態 (intimate-status)
// section renders as a collapsed-by-default native `<details>` disclosure
// when the panel's `intimate` field is present, and is entirely absent from
// the DOM when `intimate` is null or the panel is unavailable — never a
// placeholder. A single labelled control opens the skill drawer (task 5.5).
// render-equipment-breakdown-webclient: v5 trait rows carry the server-
// computed breakdown `layers`, and each stat row renders one source-tinted
// chip per layer IN PAYLOAD ORDER — a pure projection with no sorting,
// recomputation, or truncation (all ≤ 16 layers render). Layer-free rows
// render no breakdown element at all.
// The read-model logic lives in the use-status-drawer-* composables (the
// use-map-lattice / use-creation facade precedent); this SFC is the thin
// passive renderer that destructures their flat binding set below.
import { conditionLabel } from "../lib/condition_label.js";
import { useStatusDrawerCharacter } from "../composables/use-status-drawer-character.js";
import { useStatusDrawerStatus } from "../composables/use-status-drawer-status.js";
import { useStatusDrawerPersona } from "../composables/use-status-drawer-persona.js";

const props = defineProps({
  // The committed `status` v1 panel payload (vitals + conditions).
  status: { type: Object, required: true },
  // The committed `character` v5 panel payload (traits/equipment/disguise/...).
  character: { type: Object, required: true },
  // The derived low-HP presentation state (store view.vitals.lowHp).
  lowHp: { type: Boolean, default: false },
});

// `open-skill` opens the skill drawer; `persona-edit` carries one
// `{ field, text }` persona edit intent (text null clears the field) that
// AppClient dispatches as exactly one character.persona.update action.
const emit = defineEmits(["open-skill", "persona-edit"]);

// The condition prose is the shared label rule (the same label, duration,
// and modifier text the H2 chips carry in their accessible names) — one
// copy in lib/condition_label.js.
const conditionName = conditionLabel;

// The `character` v5/v7 read-model group (availability gating, traits and the
// 屬性 allowlist, disguise, guild, persona table, intimate rows, full title).
const {
  characterAvailable,
  characterReason,
  traits,
  attributeRows,
  traitValue,
  disguise,
  disguiseActive,
  displayedRows,
  guild,
  personaSections,
  intimate,
  fullTitle,
  INTIMATE_ROWS,
} = useStatusDrawerCharacter(props);

// The `status` v1 read-model group (gauges, gauge-layer guard, the full
// condition roster, and the layer-chip formatting/tint math). Call order
// preserves the original watcher registration order.
const {
  SEVERITY_GLYPHS,
  SEVERITY_LABELS,
  resources,
  formatLayerAmount,
  layerTint,
  layerLabel,
  gaugeLayers,
  VITALS,
  gaugeRatioPct,
  conditions,
} = useStatusDrawerStatus(props, traits);

// The persona inline-editor state machine (watch stays with its state).
const {
  editingField,
  editDraft,
  onPersonaInput,
  openPersonaEdit,
  cancelPersonaEdit,
  submitPersonaEdit,
} = useStatusDrawerPersona(emit, personaSections);
</script>

<template>
  <section class="character-status-drawer" data-testid="character-status-drawer">
    <h3 class="character-status-drawer__title" data-testid="character-status-drawer__title">角色狀態</h3>
    <p
      v-if="fullTitle"
      class="character-status-drawer__full-title"
      data-testid="character-status-drawer__full-title"
    >
      {{ fullTitle }}
    </p>

    <!-- The single labelled control that opens the skill drawer (task 5.5). -->
    <button
      type="button"
      class="character-status-drawer__skill-link"
      data-testid="character-status-drawer__open-skill"
      @click="$emit('open-skill')"
    >
      技能書
    </button>

    <!-- Vitals: the three gauges, rendered directly from status.resources. -->
    <section class="character-status-drawer__section" data-testid="character-status-drawer__vitals" aria-label="生命指標">
      <p class="character-status-drawer__section-label">生命量</p>
      <div class="character-status-drawer__statgrid">
        <div
          v-for="v in VITALS"
          :key="v.key"
          class="character-status-drawer__statrow"
          :data-testid="`character-status-drawer__vital--${v.key}`"
          :data-low="String(v.key === 'hp' && lowHp)"
        >
          <span class="character-status-drawer__statrow-key">
            <span class="character-status-drawer__vital-key">{{ v.label }}</span>
            <span v-if="v.key === 'hp' && lowHp" class="character-status-drawer__vital-danger" data-testid="character-status-drawer__vital-danger">
              危險
            </span>
          </span>
          <span class="character-status-drawer__statrow-value" :data-testid="`character-status-drawer__vital-value--${v.key}`">
            {{ resources?.[v.key]?.current ?? "—" }} / {{ resources?.[v.key]?.maximum ?? "—" }}
          </span>
          <!-- Breakdown chips decompose THIS gauge's maximum (guarded by
               gaugeLayers); a layer-free (or cross-payload-disagreeing) row
               renders NO element here at all. -->
          <span
            v-if="gaugeLayers(v.key).length"
            class="character-status-drawer__layerrow"
            :data-testid="`character-status-drawer__layers--${v.key}`"
          >
            <span
              v-for="(layer, index) in gaugeLayers(v.key)"
              :key="index"
              class="character-status-drawer__layer"
              :class="`character-status-drawer__layer--${layerTint(layer)}`"
              :data-source="layer.source"
              :data-testid="`character-status-drawer__layer--${v.key}--${index}`"
            >
              <span class="character-status-drawer__layer-name">{{ layerLabel(layer) }}</span>
              <span class="character-status-drawer__layer-amount">{{ formatLayerAmount(layer.kind, layer.amount) }}</span>
            </span>
          </span>
          <span class="character-status-drawer__vital-track" aria-hidden="true">
            <span
              class="character-status-drawer__vital-fill"
              :style="{ width: (gaugeRatioPct(resources?.[v.key]) ?? 0) + '%' }"
            ></span>
          </span>
        </div>
      </div>
    </section>

    <!-- The character body (task 5.3): the character-backed sections. When the
         panel is unavailable, the registry-owned reason is shown and nothing
         is fabricated. -->
    <p
      v-if="!characterAvailable && characterReason"
      class="character-status-drawer__unavailable"
      data-testid="character-status-drawer__unavailable"
      :data-reason-code="characterReason.code"
    >
      {{ characterReason.message }}
    </p>

    <!-- The 屬性 section shell stays visible in every mode: when the
         `character` panel is unavailable, the section shows the registry-
         owned reason in place of value rows — never hidden, never inventing. -->
    <section class="character-status-drawer__section" data-testid="character-status-drawer__traits" aria-label="屬性">
      <p class="character-status-drawer__section-label">屬性</p>
      <div v-if="characterAvailable" class="character-status-drawer__statgrid">
        <div
          v-for="row in attributeRows"
          :key="row.key"
          class="character-status-drawer__statrow"
          :data-testid="`character-status-drawer__trait--${row.key}`"
        >
          <span class="character-status-drawer__statrow-key">{{ row.label }}</span>
          <span class="character-status-drawer__statrow-value">{{ traitValue(row) }}</span>
          <!-- One chip per payload layer, payload order, all rendered (≤ 16
               by the payload contract); no layers → no element. -->
          <span
            v-if="row.layers?.length"
            class="character-status-drawer__layerrow"
            :data-testid="`character-status-drawer__layers--${row.key}`"
          >
            <span
              v-for="(layer, index) in row.layers"
              :key="index"
              class="character-status-drawer__layer"
              :class="`character-status-drawer__layer--${layerTint(layer)}`"
              :data-source="layer.source"
              :data-testid="`character-status-drawer__layer--${row.key}--${index}`"
            >
              <span class="character-status-drawer__layer-name">{{ layerLabel(layer) }}</span>
              <span class="character-status-drawer__layer-amount">{{ formatLayerAmount(layer.kind, layer.amount) }}</span>
            </span>
          </span>
        </div>
      </div>
      <p
        v-else
        class="character-status-drawer__section-reason"
        data-testid="character-status-drawer__traits-unavailable"
        :data-reason-code="characterReason?.code"
      >
        {{ characterReason?.message }}
      </p>
    </section>

    <!-- The equipment doll moved to the inventory drawer
         (relocate-inventory-drawer-essentials): the 角色狀態 body keeps its
         section order vitals → traits → guild → conditions → disguise →
         親密狀態 (intimate) → persona, with the intimate disclosure as the
         last main section. -->
    <section class="character-status-drawer__section" data-testid="character-status-drawer__guild" aria-label="公會">
      <p class="character-status-drawer__section-label">計數 · 公會</p>
      <div v-if="characterAvailable" class="character-status-drawer__statgrid">
        <div class="character-status-drawer__statrow" data-testid="character-status-drawer__guild-rank">
          <span class="character-status-drawer__statrow-key">公會階級</span>
          <span class="character-status-drawer__statrow-value">{{ guild?.rank ?? "未加入公會" }}</span>
        </div>
        <div class="character-status-drawer__statrow" data-testid="character-status-drawer__guild-merit">
          <span class="character-status-drawer__statrow-key">功績</span>
          <span class="character-status-drawer__statrow-value">{{ guild?.merit ?? 0 }}</span>
        </div>
      </div>
      <p
        v-else
        class="character-status-drawer__section-reason"
        data-testid="character-status-drawer__guild-unavailable"
        :data-reason-code="characterReason?.code"
      >
        {{ characterReason?.message }}
      </p>
    </section>

    <!-- The full condition roster (no cap, unlike H2's island). The status
         panel is available in every mode, so the roster renders even when the
         character panel is unavailable; the 設計稿 order is 計數・公會 →
         條件/修正 → 偽裝, so this section is placed between the two
         character-backed blocks. -->
    <section class="character-status-drawer__section" data-testid="character-status-drawer__conditions" aria-label="狀態">
      <p class="character-status-drawer__section-label">狀態</p>
      <p v-if="conditions.length === 0" class="character-status-drawer__empty" data-testid="character-status-drawer__conditions-empty">
        無狀態
      </p>
      <div v-if="conditions.length > 0" class="character-status-drawer__pillrow">
        <span
          v-for="condition in conditions"
          :key="condition.code"
          class="character-status-drawer__pill"
          :class="`character-status-drawer__pill--${condition.severity}`"
          :data-testid="`character-status-drawer__condition--${condition.code}`"
          :data-severity="condition.severity"
        >
          <span class="character-status-drawer__condition-label">{{ condition.label ?? condition.code }}</span>
          <span class="character-status-drawer__condition-stat">
            <span class="character-status-drawer__condition-glyph" aria-hidden="true">
              {{ SEVERITY_GLYPHS[condition.severity] ?? "◆" }}
            </span>
            <span class="character-status-drawer__condition-severity">{{ SEVERITY_LABELS[condition.severity] ?? condition.severity }}</span>
            <span
              v-if="typeof condition.remaining_seconds === 'number'"
              class="character-status-drawer__condition-timer"
              :data-testid="`character-status-drawer__condition-timer--${condition.code}`"
            >
              剩 {{ condition.remaining_seconds }} 秒
            </span>
            <span
              v-for="(value, key) in (condition.modifiers || {})"
              :key="key"
              class="character-status-drawer__condition-mod"
              :data-testid="`character-status-drawer__condition-mod--${condition.code}-${key}`"
            >
              {{ key }} {{ value }}
            </span>
          </span>
        </span>
      </div>
    </section>

    <!-- The 偽裝 section shell stays visible in every mode: when the
         `character` panel is unavailable, the section shows the registry-
         owned reason instead of the 真值 / 顯示 comparison. -->
    <section class="character-status-drawer__section" data-testid="character-status-drawer__disguise" :data-active="String(disguiseActive)" aria-label="偽裝">
      <p class="character-status-drawer__section-label">偽裝</p>
      <template v-if="characterAvailable">
        <template v-if="disguiseActive">
          <p class="character-status-drawer__disguise-description" data-testid="character-status-drawer__disguise-description">
            {{ disguise.description }}
          </p>
          <div
            v-for="row in displayedRows"
            :key="row.key"
            class="character-status-drawer__disguise-row"
            :data-testid="`character-status-drawer__disguise--${row.key}`"
          >
            <span class="character-status-drawer__disguise-key">{{ row.label }}</span>
            <span v-if="row.trueValue !== null" class="character-status-drawer__disguise-true" data-testid="character-status-drawer__disguise-true">
              真 {{ row.trueValue }}
            </span>
            <span class="character-status-drawer__disguise-displayed" data-testid="character-status-drawer__disguise-displayed">
              顯 {{ row.value }}
            </span>
          </div>
          <p class="character-status-drawer__disguise-note" data-testid="character-status-drawer__disguise-note">
            戰鬥永遠以真值決算，顯示值只影響外觀、公會登記與鑑定。
          </p>
        </template>
        <p v-else class="character-status-drawer__disguise-inactive" data-testid="character-status-drawer__disguise-inactive">
          目前沒有偽裝狀態。
        </p>
      </template>
      <p
        v-else
        class="character-status-drawer__section-reason"
        data-testid="character-status-drawer__disguise-unavailable"
        :data-reason-code="characterReason?.code"
      >
        {{ characterReason?.message }}
      </p>
    </section>

    <!-- The 親密狀態 (intimate status) section: a native `<details>`
         disclosure, collapsed by default, rendered after 偽裝 and before
         the wallet row. It is entirely absent from the DOM when `intimate`
         is null or the `character` panel is unavailable — never a placeholder
         or a collapsed-empty widget. -->
    <details
      v-if="intimate"
      class="character-status-drawer__section character-status-drawer__intimate"
      data-testid="character-status-drawer__intimate"
      aria-label="親密狀態"
    >
      <summary class="character-status-drawer__intimate-summary" data-testid="character-status-drawer__intimate-summary">
        <span class="character-status-drawer__section-label">親密狀態</span>
        <span class="character-status-drawer__intimate-marker" aria-hidden="true">›</span>
      </summary>
      <p class="character-status-drawer__intimate-hint" data-testid="character-status-drawer__intimate-hint">
        詞彙封閉；數值依設定折線/級別顯示。
      </p>
      <div class="character-status-drawer__statgrid">
        <div
          v-for="row in INTIMATE_ROWS"
          :key="row.key"
          class="character-status-drawer__statrow"
          :data-testid="`character-status-drawer__intimate--${row.key}`"
        >
          <span class="character-status-drawer__statrow-key">{{ row.label }}</span>
          <span class="character-status-drawer__statrow-value">
            {{ row.key === "climax_today" ? `${intimate.climax_today} 次` : intimate[row.key] }}
          </span>
        </div>
      </div>
    </details>

    <!-- The single drawer-layer wallet moved to the inventory drawer's
         shared header (relocate-inventory-drawer-essentials); the 角色狀態
         body renders no balance of its own (and never a zero). -->
    <!-- The persona area (add-persona-edit-surface D4): four labelled
         sections in 個性／生平／習慣／背景 order. Each shows the committed
         verbatim text or the localized 未設定 placeholder, plus an inline
         edit affordance that submits exactly one persona-edit intent
         ({ field, text }; a blank draft submits null). When the
         `character` panel is unavailable the area stays visible, is marked
         with the registry-owned reason, and offers no edit controls. -->
    <section class="character-status-drawer__section" data-testid="character-status-drawer__persona" aria-label="設定">
      <p
        v-if="!characterAvailable"
        class="character-status-drawer__section-reason"
        data-testid="character-status-drawer__persona-unavailable"
        :data-reason-code="characterReason?.code"
      >
        {{ characterReason?.message }}
      </p>
      <template v-else>
        <div
          v-for="section in personaSections"
          :key="section.key"
          class="character-status-drawer__persona-block"
          :data-testid="`character-status-drawer__persona--${section.key}`"
        >
        <p class="character-status-drawer__section-label">{{ section.label }}</p>
        <p
          v-if="section.value !== null"
          class="character-status-drawer__persona-background"
          :data-testid="`character-status-drawer__persona-value--${section.key}`"
        >
          {{ section.value }}
        </p>
        <p v-else class="character-status-drawer__persona-empty" :data-testid="`character-status-drawer__persona-empty--${section.key}`">
          未設定
        </p>
        <button
          v-if="editingField !== section.key"
          type="button"
          class="ui-btn ui-btn--sm character-status-drawer__persona-edit"
          :data-testid="`character-status-drawer__persona-edit--${section.key}`"
          @click="openPersonaEdit(section)"
        >
          編輯{{ section.label }}
        </button>
        <div v-else class="character-status-drawer__persona-editor">
          <textarea
            rows="3"
            :aria-label="section.label"
            @input="onPersonaInput"
            :data-testid="`character-status-drawer__persona-input--${section.key}`"
            v-model="editDraft"
          ></textarea>
          <div class="character-status-drawer__persona-editor-buttons">
            <button
              type="button"
              class="ui-btn ui-btn--sm ui-btn--primary character-status-drawer__persona-submit"
              :data-testid="`character-status-drawer__persona-submit--${section.key}`"
              @click="submitPersonaEdit(section)"
            >
              儲存
            </button>
            <button
              type="button"
              class="ui-btn ui-btn--sm character-status-drawer__persona-cancel"
              :data-testid="`character-status-drawer__persona-cancel--${section.key}`"
              @click="cancelPersonaEdit"
            >
              取消
            </button>
          </div>
        </div>
        </div>
</template>
    </section>
  </section>
</template>

<style scoped src="./character-status-drawer.css"></style>
