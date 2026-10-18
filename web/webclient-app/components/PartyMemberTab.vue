<script setup>
// PartyMemberTab (webclient-party-window-member-tab, design §6.1): the party
// window's 成員 tab. The list column is the portrait nameplate (the shared
// avatar renderer, name, ▼ 倒地, HP/MP/SP from the committed `party` row);
// the detail column and its action bar read the committed `party_member`
// panel for the viewed member:
//
//   * a companion: 羈絆 stage with its pips, 同行身分 tags and 親密狀態, with
//     請其離隊 (two steps), 人物卡 (the NPC persona editor) and 附身 or
//     解除附身, each from its server descriptor;
//   * the commander: the four persona fields and 親密狀態, with 編輯人物設定
//     (the inline persona editor moved here from the character-status drawer);
//   * 空位 (`member` null): the invite target and the committed
//     `explore.party_invite` affordance.
//
// Every enablement and reason is a committed descriptor; the tab shows state
// and committed reasons only, never rule explanations (design §3.4). It
// renders identically whether or not the player is possessing: it has no
// possession input at all.
import { computed, nextTick, ref, watch } from "vue";
import ActionBar from "./ActionBar.vue";
import AvatarArtwork from "./AvatarArtwork.vue";
import ListDetail from "./ListDetail.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { portraitFor } from "./party-helpers.js";
import {
  INTIMATE_ROWS,
  PERSONA_SECTIONS,
  descriptorAction,
  findDescriptor,
  gaugePercent,
  inviteResolution,
  panelReason,
} from "./party-window-model.js";
import { useMemberPersona } from "../composables/use-member-persona.js";

const props = defineProps({
  // The selected committed `party` v3 row, or null for the 空位 entry.
  member: { type: Object, default: null },
  // The committed `party_member` v1 panel (the viewed member's facts).
  partyMember: { type: Object, default: null },
  // The committed `art` panel (the nameplate's portrait catalog).
  artPanel: { type: Object, default: null },
  // The committed `exploration.interact` targets (the 空位 invite affordance).
  interactTargets: { type: Array, default: () => [] },
});

const emit = defineEmits(["action", "open-npc-persona", "persona-edit"]);

const root = ref(null);

// ---------------------------------------------------------------- detail

const memberReason = computed(() => panelReason(props.partyMember));
// The panel's facts are shown only for the member they describe; a
// transient disagreement renders no detail rather than another member's.
const detail = computed(() => {
  const panel = props.partyMember;
  if (!props.member || !panel || panel.available !== true) return null;
  if (panel.member_id !== props.member.identity) return null;
  return panel;
});
const companion = computed(() => (detail.value?.role === "companion" ? detail.value.companion : null));
const commander = computed(() => (detail.value?.role === "commander" ? detail.value.commander : null));
const intimate = computed(() => companion.value?.intimate ?? commander.value?.intimate ?? null);

const bondLabel = computed(() => {
  const bond = companion.value?.bond;
  return bond ? `第 ${bond.step} 階，共 ${bond.steps} 階` : "";
});

const possessDescriptor = computed(() =>
  findDescriptor(companion.value?.actions, ["explore.possess", "explore.possess_release"]),
);
const leaveDescriptor = computed(() => findDescriptor(companion.value?.actions, "explore.party_leave"));
const npcPersonaDescriptor = computed(() => findDescriptor(companion.value?.actions, "npc.persona.read"));
const personaEditDescriptor = computed(() => findDescriptor(commander.value?.actions, "character.persona.update"));

// ---------------------------------------------------------------- leave

// The armed state belongs to one companion and disarms when the selection,
// the descriptor or the tab goes away (the quest drawer's abandon pattern).
const armedId = ref(null);
const armed = computed(
  () => !!companion.value && armedId.value === props.member?.identity && leaveDescriptor.value?.enabled === true,
);
watch(
  () => [props.member?.identity ?? null, leaveDescriptor.value?.enabled === true],
  () => {
    if (!armed.value) armedId.value = null;
  },
);

async function focusBarButton(key) {
  await nextTick();
  root.value?.querySelector(`[data-testid="action-bar__btn--${key}"]`)?.focus();
}

function arm() {
  armedId.value = props.member.identity;
  focusBarButton("leave-cancel");
}

function disarm() {
  armedId.value = null;
  focusBarButton("leave");
}

function confirmLeave() {
  const descriptor = leaveDescriptor.value;
  armedId.value = null;
  if (descriptor?.enabled !== true) return;
  emit("action", { action_id: descriptor.action_id, payload: { ...descriptor.params } });
}

// The window's close guard: a close attempt (Escape, ✕, the scrim) while the
// leave is armed cancels the confirmation instead and sends nothing.
function cancelArmed() {
  if (!armed.value) return false;
  disarm();
  return true;
}

// The whole guard: the armed leave first, then an unsaved persona draft,
// which refuses one close attempt and says so in the action bar.
function guardClose() {
  if (cancelArmed()) return true;
  if (draftDirty.value && !closeWarned.value) {
    closeWarned.value = true;
    return true;
  }
  return false;
}

defineExpose({ cancelArmed, guardClose });

// ---------------------------------------------------------------- persona

const personaSections = computed(() => {
  const persona = commander.value?.persona ?? null;
  if (!persona) return [];
  return PERSONA_SECTIONS.map((section) => ({ ...section, value: persona[section.key] ?? null }));
});
const { editingField, editDraft, onPersonaInput, openPersonaEdit, cancelPersonaEdit, submitPersonaEdit } =
  useMemberPersona(emit, personaSections);

const editing = ref(false);
// An open field whose draft differs from its committed value.
const draftDirty = computed(() => {
  if (editingField.value === null) return false;
  const section = personaSections.value.find((entry) => entry.key === editingField.value);
  return (editDraft.value ?? "").trim() !== (section?.value ?? "").trim();
});
const UNSAVED_TEXT = "尚有未儲存的人物設定。";
const closeWarned = ref(false);
watch([editingField, editDraft], () => {
  closeWarned.value = false;
});
watch(
  () => personaEditDescriptor.value?.enabled === true,
  (enabled) => {
    if (!enabled) {
      editing.value = false;
      cancelPersonaEdit();
    }
  },
);

function stopEditing() {
  editing.value = false;
  cancelPersonaEdit();
}

// ---------------------------------------------------------------- 空位

const invite = computed(() => inviteResolution(props.interactTargets));

// ---------------------------------------------------------------- actions

const barActions = computed(() => {
  if (!props.member) {
    return [{ key: "invite", label: "邀請同行", tone: "primary", enabled: invite.value.enabled, reason: invite.value.enabled ? null : invite.value.reason }];
  }
  if (commander.value) {
    if (editing.value) {
      // 完成編輯 never discards an open draft: save or cancel it first.
      const open = editingField.value !== null;
      return [{ key: "persona-done", label: "完成編輯", tone: "gold", enabled: !open, reason: open ? "請先儲存或取消正在編輯的欄位。" : null }];
    }
    return [descriptorAction(personaEditDescriptor.value, { key: "persona-edit", label: "編輯人物設定", tone: "gold" })];
  }
  if (!companion.value) return [];
  if (armed.value) {
    return [
      { key: "leave-cancel", label: "取消" },
      { key: "leave-confirm", label: "確認請其離隊", tone: "primary" },
    ];
  }
  const possess = possessDescriptor.value;
  return [
    descriptorAction(leaveDescriptor.value, { key: "leave", label: "請其離隊…", tone: "ghost" }),
    descriptorAction(npcPersonaDescriptor.value, { key: "npc-persona", label: "人物卡", tone: "gold" }),
    descriptorAction(possess, {
      key: "possess",
      label: possess?.action_id === "explore.possess_release" ? "解除附身" : "附身",
      tone: "primary",
    }),
  ];
});

function onBarAction(key) {
  switch (key) {
    case "invite": {
      const target = invite.value.target;
      if (!invite.value.enabled || !target) return;
      emit("action", { action_id: "explore.party_invite", payload: { npc_id: target.identity, message: "" } });
      return;
    }
    case "persona-edit":
      editing.value = true;
      return;
    case "persona-done":
      stopEditing();
      return;
    case "leave":
      arm();
      return;
    case "leave-cancel":
      disarm();
      return;
    case "leave-confirm":
      confirmLeave();
      return;
    case "npc-persona": {
      const npcId = npcPersonaDescriptor.value?.params?.npc_id;
      if (Number.isSafeInteger(npcId)) emit("open-npc-persona", npcId);
      return;
    }
    case "possess": {
      const descriptor = possessDescriptor.value;
      if (descriptor?.enabled === true) {
        emit("action", { action_id: descriptor.action_id, payload: { ...descriptor.params } });
      }
      return;
    }
    default:
  }
}

// ---------------------------------------------------------------- nameplate

const gauges = computed(() => {
  const row = props.member;
  if (!row) return [];
  return [
    { key: "hp", label: "HP", color: "var(--vit-hp)", current: row.hp_current, maximum: row.hp_maximum },
    { key: "mp", label: "MP", color: "var(--vit-mp)", current: row.mp_current, maximum: row.mp_maximum },
    { key: "sp", label: "SP", color: "var(--vit-sp)", current: row.sp_current, maximum: row.sp_maximum },
  ];
});
const portrait = computed(() => (props.member ? portraitFor(props.artPanel, props.member.portrait_ref) : null));
const hasReference = computed(() => props.member?.portrait_ref !== null && props.member?.portrait_ref !== undefined);
</script>

<template>
  <div ref="root" class="party-member-tab" data-testid="party-member-tab" :data-member="member ? member.identity : 'empty'">
    <ListDetail variant="portrait" list-label="成員名牌" detail-label="成員詳情">
      <template #rail><slot name="rail" /></template>

      <template #list>
        <div class="party-member-tab__plate" data-testid="party-member-tab__plate">
          <template v-if="member">
            <div class="party-member-tab__art" :class="{ 'is-down': member.knocked_out }">
              <AvatarArtwork
                :artwork="portrait"
                :panel="artPanel"
                :has-reference="hasReference"
                :name="member.display_name"
                :initial-of="member.display_name"
              />
            </div>
            <h3 class="party-member-tab__name" data-testid="party-member-tab__name">{{ member.display_name }}</h3>
            <p v-if="member.knocked_out" class="party-member-tab__down" data-testid="party-member-tab__down">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path :d="glyphPath('knocked_out')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('knocked_out')" />
              </svg>倒地
            </p>
            <div
              v-for="gauge in gauges"
              :key="gauge.key"
              class="party-member-tab__gauge"
              :data-testid="`party-member-tab__gauge--${gauge.key}`"
            >
              <span :style="{ color: gauge.color }">{{ gauge.label }}</span>
              <span class="party-member-tab__track"><i :style="{ width: `${gaugePercent(gauge.current, gauge.maximum)}%`, background: gauge.color }"></i></span>
              <span class="party-member-tab__value">{{ gauge.current }} / {{ gauge.maximum }}</span>
            </div>
          </template>
          <template v-else>
            <div class="party-member-tab__art party-member-tab__art--empty" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path :d="glyphPath('plus')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('plus')" />
              </svg>
            </div>
            <h3 class="party-member-tab__name">空位</h3>
          </template>
        </div>
      </template>

      <template #detail>
        <!-- 空位: the invite target from the committed affordance. -->
        <template v-if="!member">
          <h4 class="party-member-tab__sech">可邀請</h4>
          <p v-if="invite.target" class="party-member-tab__invite" data-testid="party-member-tab__invite-target">
            <span class="party-member-tab__initial" aria-hidden="true">{{ Array.from(invite.target.display_name || "")[0] }}</span>{{ invite.target.display_name }}
          </p>
        </template>

        <p
          v-else-if="memberReason"
          class="party-member-tab__reason"
          data-testid="party-member-tab__unavailable"
          :data-reason-code="memberReason.code || undefined"
        >{{ memberReason.message }}</p>

        <!-- A companion: bond, membership, intimate state. -->
        <template v-else-if="companion">
          <h4 class="party-member-tab__sech">羈絆</h4>
          <div class="party-member-tab__bond" data-testid="party-member-tab__bond">
            <span class="party-member-tab__stage">{{ companion.bond.stage }}</span>
            <span class="party-member-tab__pips" role="img" :aria-label="bondLabel" data-testid="party-member-tab__pips">
              <i v-for="n in companion.bond.steps" :key="n" :class="{ 'is-on': n <= companion.bond.step }"></i>
            </span>
          </div>
          <h4 class="party-member-tab__sech">同行身分</h4>
          <div class="party-member-tab__tags" data-testid="party-member-tab__membership">
            <span v-if="companion.membership.general" class="party-member-tab__tag">一般同伴</span>
            <span
              v-for="commission in companion.membership.temporary_commissions"
              :key="`${commission.quest_id}|${commission.role_id}`"
              class="party-member-tab__tag party-member-tab__tag--seal"
              data-testid="party-member-tab__commission"
            >委託：{{ commission.label }}</span>
          </div>
        </template>

        <!-- The commander: the four persona fields, editable in place. -->
        <template v-else-if="commander">
          <h4 class="party-member-tab__sech">人物設定</h4>
          <div
            v-for="section in personaSections"
            :key="section.key"
            class="party-member-tab__letter"
            :data-testid="`party-member-tab__persona--${section.key}`"
          >
            <b>{{ section.label }}</b>
            <template v-if="editingField !== section.key">
              <span v-if="section.value !== null" :data-testid="`party-member-tab__persona-value--${section.key}`">{{ section.value }}</span>
              <span v-else class="party-member-tab__unset" :data-testid="`party-member-tab__persona-empty--${section.key}`">未設定</span>
              <button
                v-if="editing"
                type="button"
                class="party-member-tab__mini"
                :data-testid="`party-member-tab__persona-edit--${section.key}`"
                @click="openPersonaEdit(section)"
              >編輯{{ section.label }}</button>
            </template>
            <div v-else class="party-member-tab__editor">
              <textarea
                v-model="editDraft"
                rows="3"
                :aria-label="section.label"
                :data-testid="`party-member-tab__persona-input--${section.key}`"
                @input="onPersonaInput"
              ></textarea>
              <div class="party-member-tab__editor-buttons">
                <button
                  type="button"
                  class="party-member-tab__mini party-member-tab__mini--primary"
                  :data-testid="`party-member-tab__persona-submit--${section.key}`"
                  @click="submitPersonaEdit(section)"
                >儲存</button>
                <button
                  type="button"
                  class="party-member-tab__mini"
                  :data-testid="`party-member-tab__persona-cancel--${section.key}`"
                  @click="cancelPersonaEdit"
                >取消</button>
              </div>
            </div>
          </div>
        </template>

        <template v-if="intimate">
          <h4 class="party-member-tab__sech">親密狀態</h4>
          <div class="party-member-tab__intimate" data-testid="party-member-tab__intimate">
            <div v-for="row in INTIMATE_ROWS" :key="row.key"><span>{{ row.label }}</span><b>{{ intimate[row.key] }}</b></div>
          </div>
        </template>
      </template>

      <template #actions>
        <ActionBar :actions="barActions" @action="onBarAction">
          <template v-if="armed" #lead>
            <p class="party-member-tab__warn" role="alert" data-testid="party-member-tab__leave-warning">{{ member.display_name }}會離開隊伍。</p>
          </template>
          <template v-else-if="closeWarned" #lead>
            <p class="party-member-tab__warn" role="alert" data-testid="party-member-tab__unsaved-warning">{{ UNSAVED_TEXT }}</p>
          </template>
        </ActionBar>
      </template>
    </ListDetail>
  </div>
</template>

<style scoped>
/* The approved prototype's 成員 tab (docs/design/party-member-management/
   tabs/MemberTab.vue and prototype.css `.pm-sech`, `.pm-gauge`, `.pm-tag`). */
.party-member-tab {
  --party-member-line: rgba(185, 154, 96, 0.28);
  --party-member-intimate: #d98aa8;
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.party-member-tab__plate {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.party-member-tab__art {
  position: relative;
  flex: 1;
  min-height: calc(220px * var(--ui-scale));
  margin-bottom: var(--sp-3);
  overflow: hidden;
  background: linear-gradient(180deg, #3a3329, #15171c 80%);
  border: calc(1px * var(--ui-scale)) solid var(--party-member-line);
  border-radius: var(--radius-sm);
}

.party-member-tab__art :deep(.avatar-artwork) {
  position: absolute;
  inset: 0;
}

/* Without a real portrait the nameplate stands the name's initial as a large
   seal-like glyph on the art ground, so the frame never reads as empty. */
.party-member-tab__art :deep(.avatar-artwork__initial) {
  color: var(--gold-400);
  font-family: var(--f-display);
  font-size: var(--text-4xl);
  text-shadow: 0 0 calc(18px * var(--ui-scale)) rgba(228, 200, 142, 0.25);
  background: radial-gradient(60% 50% at 50% 42%, rgba(185, 154, 96, 0.12), transparent 70%);
}

.party-member-tab__art.is-down {
  filter: grayscale(0.8) brightness(0.6);
}

.party-member-tab__art--empty {
  display: grid;
  place-items: center;
  color: var(--paper-700);
  font-size: var(--text-4xl);
  background: none;
  border-style: dashed;
}

.party-member-tab__art--empty svg {
  width: 1.4em;
  height: 1.4em;
}

.party-member-tab__name {
  margin: 0;
  color: var(--paper-50);
  font: var(--text-2xl) var(--f-display);
}

.party-member-tab__down {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  margin: var(--sp-1) 0 0;
  color: var(--seal-400);
  font-size: var(--text-xs);
}

.party-member-tab__down svg {
  width: 1em;
  height: 1em;
}

.party-member-tab__gauge {
  display: grid;
  grid-template-columns: calc(30px * var(--ui-scale)) 1fr auto;
  gap: var(--sp-2);
  align-items: center;
  margin-top: var(--sp-1);
  font-size: var(--text-xs);
}

.party-member-tab__track {
  height: calc(6px * var(--ui-scale));
  overflow: hidden;
  background: #25272b;
  border-radius: calc(3px * var(--ui-scale));
}

.party-member-tab__track i {
  display: block;
  height: 100%;
}

.party-member-tab__value {
  min-width: calc(64px * var(--ui-scale));
  color: var(--paper-100);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.party-member-tab__sech {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: var(--sp-4) 0 var(--sp-2);
  color: var(--gold-300);
  font: var(--text-base) var(--f-display);
  letter-spacing: 0.06em;
}

.party-member-tab__sech:first-child {
  margin-top: 0;
}

.party-member-tab__sech::after {
  content: "";
  flex: 1;
  height: calc(1px * var(--ui-scale));
  background: linear-gradient(90deg, var(--party-member-line), transparent);
}

.party-member-tab__reason {
  margin: 0;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.party-member-tab__bond {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
}

.party-member-tab__stage {
  color: var(--paper-50);
  font: var(--text-xl) var(--f-display);
}

.party-member-tab__pips {
  display: flex;
  gap: var(--sp-1);
}

.party-member-tab__pips i {
  width: calc(22px * var(--ui-scale));
  height: calc(8px * var(--ui-scale));
  background: #2a2c30;
  transform: skewX(-20deg);
}

.party-member-tab__pips i.is-on {
  background: var(--gold-500);
  box-shadow: 0 0 calc(6px * var(--ui-scale)) var(--gold-glow);
}

.party-member-tab__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.party-member-tab__tag {
  padding: calc(2px * var(--ui-scale)) var(--sp-2);
  color: var(--paper-200);
  font: var(--text-xs) var(--f-sans);
  border: calc(1px * var(--ui-scale)) solid var(--party-member-line);
  border-radius: calc(2px * var(--ui-scale));
}

.party-member-tab__tag--seal {
  color: var(--seal-400);
  border-color: var(--seal-700);
}

.party-member-tab__letter {
  margin-bottom: var(--sp-2);
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-200);
  font: var(--text-md) / 1.85 var(--f-serif);
  background: rgba(0, 0, 0, 0.18);
  border-left: calc(2px * var(--ui-scale)) solid var(--gold-600);
}

.party-member-tab__letter b {
  display: block;
  color: var(--gold-400);
  font: 500 var(--text-xs) var(--f-sans);
  letter-spacing: 0.1em;
}

.party-member-tab__unset {
  color: var(--paper-500);
  font-style: italic;
}

.party-member-tab__mini {
  display: block;
  margin-top: var(--sp-1);
  padding: var(--sp-1) var(--sp-3);
  color: var(--paper-300);
  font: var(--text-xs) var(--f-sans);
  background: transparent;
  border: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: color var(--motion-fast) ease, border-color var(--motion-fast) ease;
}

.party-member-tab__mini:hover {
  color: var(--paper-50);
  border-color: var(--gold-500);
}

.party-member-tab__mini:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-member-tab__mini--primary {
  color: var(--paper-50);
  background: var(--seal-500);
  border-color: var(--seal-500);
}

.party-member-tab__editor textarea {
  box-sizing: border-box;
  width: 100%;
  padding: var(--sp-2);
  color: var(--paper-100);
  font: var(--text-sm) / 1.7 var(--f-serif);
  background: var(--ink-860);
  border: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-radius: var(--radius-sm);
  resize: vertical;
}

.party-member-tab__editor-buttons {
  display: flex;
  gap: var(--sp-2);
}

.party-member-tab__intimate {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-2);
}

.party-member-tab__intimate div {
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-500);
  font-size: var(--text-xs);
  border: calc(1px * var(--ui-scale)) solid var(--party-member-line);
  border-radius: var(--radius-sm);
}

.party-member-tab__intimate b {
  display: block;
  color: var(--party-member-intimate);
  font: 500 var(--text-md) var(--f-sans);
}

.party-member-tab__invite {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0;
  color: var(--paper-100);
}

.party-member-tab__initial {
  display: grid;
  place-items: center;
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
  color: var(--paper-100);
  font: var(--text-sm) var(--f-serif);
  background: radial-gradient(circle at 50% 30%, #3a332a, #16181c);
  border: calc(1px * var(--ui-scale)) solid var(--gold-600);
  border-radius: 50%;
}

/* The destructive leave stands apart at the bar's left end, before any
   committed reason, as in the prototype; the decisive actions keep the
   right end. */
.party-member-tab :deep([data-testid="action-bar__btn--leave"]) {
  order: -1;
}

.party-member-tab__warn {
  margin: 0;
  color: var(--warn);
  font-size: var(--text-xs);
}

@media (prefers-reduced-motion: reduce) {
  .party-member-tab__mini {
    transition: none;
  }
}
</style>
