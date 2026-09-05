<script setup>
// PartyDrawer (webclient-align-05-party-hud, design D1/D2/D3):
// the 同伴 · 隊伍 drawer body, mounted inside the shared HudDrawer chrome.
// Renders the committed `party.slots` compbig rows with avatar initial fallback,
// display name, bond stage line, HP bar + numerals, joined combat token,
// 請其離隊 confirmation flow, an 空位 row with stage-name-word invite rule,
// and the three fixed 跟隨規則 lines verbatim.
import { computed, ref, watch } from "vue";
import {
  buildCombatTokenMap,
  hpFillRatio,
  portraitFor,
  portraitGlyph,
} from "./party-helpers.js";

const props = defineProps({
  // The committed `party.slots` array.
  slots: { type: Array, default: () => [] },
  // The committed combat participants (joined by identity for combat token).
  combatParticipants: { type: Array, default: () => [] },
  // The committed `art` panel (the portrait catalog source).
  artPanel: { type: Object, default: null },
  // The committed `exploration.interact` targets (for invite/leave affordance resolution).
  interactTargets: { type: Array, default: () => [] },
  // Current game mode ("exploration", "combat", "creation").
  mode: { type: String, default: "exploration" },
  // Whether the party panel read model is available.
  available: { type: Boolean, default: true },
  // Optional registry-owned reason message when unavailable.
  reason: { type: String, default: "" },
  releaseAffordance: { type: Object, default: null },
  affordances: { type: Array, default: () => [] },
});

const emit = defineEmits(["action", "close"]);

const MAX_PARTY_SLOTS = 4;

const safeSlots = computed(() => (Array.isArray(props.slots) ? props.slots : []));
const emptyCount = computed(() => Math.max(0, MAX_PARTY_SLOTS - safeSlots.value.length));
const tokenById = computed(() => buildCombatTokenMap(props.combatParticipants));

// Local confirmation state: holds the identity of the companion being dismissed.
const confirmingLeaveId = ref(null);

// Reset confirmation whenever slots or game mode change (prevent stale confirmation).
watch(() => props.slots, () => {
  confirmingLeaveId.value = null;
}, { deep: true });

watch(() => props.mode, () => {
  confirmingLeaveId.value = null;
});

function combatToken(slot) {
  if (!slot || slot.identity == null) return null;
  return tokenById.value.get(String(slot.identity)) || null;
}

function portraitEntry(slot) {
  return portraitFor(props.artPanel, slot.portrait_ref);
}

// Find the companion's leave affordance from committed interact targets.
function leavePrecondition(slot) {
  if (props.mode !== "exploration") {
    return { enabled: false, reason: "戰鬥中無法調整隊伍" };
  }
  const target = (props.interactTargets || []).find(
    (t) => String(t.identity) === String(slot.identity),
  );
  if (!target) {
    // If companion is in the party but not present in current interact targets
    return { enabled: true, reason: null };
  }
  const leaveAffordance = (target.affordances || []).find(
    (a) => a.action_id === "explore.party_leave",
  );
  if (!leaveAffordance) {
    return { enabled: true, reason: null };
  }
  return {
    enabled: leaveAffordance.enabled !== false,
    reason: leaveAffordance.disabled_reason?.message || null,
  };
}

function armLeave(slot) {
  confirmingLeaveId.value = slot.identity;
}

function cancelLeave() {
  confirmingLeaveId.value = null;
}

function confirmLeave(slot) {
  if (confirmingLeaveId.value !== slot.identity) return;
  // Re-verify leave precondition is still enabled in current context
  if (!leavePrecondition(slot).enabled) {
    confirmingLeaveId.value = null;
    return;
  }
  // Verify slot is still in current slots
  const exists = safeSlots.value.some((s) => s.identity === slot.identity);
  if (!exists) {
    confirmingLeaveId.value = null;
    return;
  }
  emit("action", {
    action_id: "explore.party_leave",
    payload: { npc_id: slot.identity },
  });
  confirmingLeaveId.value = null;
}

function possessPrecondition(slot) {
  if (props.mode !== "exploration") {
    return { visible: true, enabled: false, reason: "戰鬥中無法附身" };
  }
  const target = (props.interactTargets || []).find(
    (t) => String(t.identity) === String(slot.identity),
  );
  let possessAffordance = null;
  if (target) {
    possessAffordance = (target.affordances || []).find(
      (a) => a.action_id === "explore.possess",
    );
  }
  if (!possessAffordance && Array.isArray(props.affordances)) {
    possessAffordance = props.affordances.find(
      (a) => a.action_id === "explore.possess" && String(a.params?.npc_id) === String(slot.identity),
    );
  }
  if (!possessAffordance) {
    return { visible: true, enabled: false, reason: "對方不在這裡。" };
  }
  const disabledMsg = possessAffordance.disabled_reason?.message || (Array.isArray(possessAffordance.disabled_reason) ? possessAffordance.disabled_reason[1] : null);
  return {
    visible: true,
    enabled: possessAffordance.enabled !== false,
    reason: disabledMsg,
  };
}

function onPossess(slot) {
  const prec = possessPrecondition(slot);
  if (!prec.enabled) return;
  emit("action", {
    action_id: "explore.possess",
    payload: { npc_id: slot.identity },
  });
}

const activeReleaseAffordance = computed(() => {
  if (props.releaseAffordance) return props.releaseAffordance;
  if (Array.isArray(props.affordances)) {
    return props.affordances.find((a) => a.action_id === "explore.possess_release") || null;
  }
  return null;
});

function onRelease() {
  const aff = activeReleaseAffordance.value;
  if (!aff) return;
  const npcId = aff.params?.npc_id;
  emit("action", {
    action_id: "explore.possess_release",
    payload: { npc_id: npcId },
  });
}

// Deterministic invite target selection:
// Choose the first target in committed target order with an enabled `explore.party_invite` affordance.
// If none enabled, look for any target with an `explore.party_invite` affordance for its disabled reason.
const inviteResolution = computed(() => {
  if (props.mode !== "exploration") {
    return { target: null, enabled: false, reason: "戰鬥中無法調整隊伍" };
  }
  const targets = props.interactTargets || [];
  let firstDisabledReason = null;

  for (const t of targets) {
    const inviteAff = (t.affordances || []).find(
      (a) => a.action_id === "explore.party_invite",
    );
    if (inviteAff) {
      if (inviteAff.enabled !== false) {
        return { target: t, enabled: true, reason: null };
      }
      if (!firstDisabledReason && inviteAff.disabled_reason?.message) {
        firstDisabledReason = inviteAff.disabled_reason.message;
      }
    }
  }

  return {
    target: null,
    enabled: false,
    reason: firstDisabledReason || "邀請需當地自由 NPC，且羈絆達「親睦」階段",
  };
});

function onInviteCurrentNpc() {
  const res = inviteResolution.value;
  if (!res.enabled || !res.target) return;
  emit("action", {
    action_id: "explore.party_invite",
    payload: { npc_id: res.target.identity, message: "" },
  });
}
</script>

<template>
  <section class="party-drawer" data-testid="party-drawer">
    <template v-if="!available">
      <p class="party-drawer__unavailable" data-testid="party-drawer__unavailable">
        {{ reason || "隊伍資訊目前無法顯示" }}
      </p>
    </template>
    <template v-else>
    <p class="party-drawer__intro" data-testid="party-drawer__intro">
      同伴是正式 NPC，隨你移動與戰鬥。羈絆 7 階（數值隱藏）；戰鬥中 HP 歸零改為「失去意識」，時鐘重生。無法指揮同伴，只能管理自己的行動。
    </p>

    <!-- Possession release banner -->
    <div
      v-if="activeReleaseAffordance"
      class="party-drawer__release-banner"
      data-testid="party-drawer__release-banner"
    >
      <span class="party-drawer__release-text">目前正處於附身狀態</span>
      <button
        type="button"
        class="btn-release"
        data-testid="party-drawer__release-btn"
        @click="onRelease"
      >
        歸位
      </button>
    </div>

    <!-- Companion rows -->
    <div
      v-for="slot in safeSlots"
      :key="slot.identity"
      class="compbig"
      :data-testid="`party-drawer__row-${slot.identity}`"
    >
      <div class="av" data-testid="party-drawer__avatar">
        <img
          v-if="portraitEntry(slot)"
          class="av-img"
          :src="portraitEntry(slot).url"
          :alt="slot.display_name"
        />
        <span v-else class="mono av-glyph">{{ portraitGlyph(slot.display_name) }}</span>
      </div>
      <div class="info">
        <div class="nm" data-testid="party-drawer__name">
          {{ slot.display_name }}
        </div>
        <div class="bondrow" data-testid="party-drawer__bond">
          羈絆 · <i>{{ slot.bond_stage }}</i>
        </div>
        <div class="cbar" data-testid="party-drawer__hp-bar">
          <div
            class="f"
            :style="{ width: `${hpFillRatio(slot.hp_current, slot.hp_maximum)}%` }"
          ></div>
        </div>
        <div class="meta" data-testid="party-drawer__meta">
          <span>HP {{ slot.hp_current }}/{{ slot.hp_maximum }}</span>
          <span
            v-if="combatToken(slot)"
            class="ko"
            data-testid="party-drawer__combat-token"
          >參戰 {{ combatToken(slot) }}</span>
        </div>
        <div class="acts" data-testid="party-drawer__acts">
          <button
            type="button"
            class="btn-possess"
            data-testid="party-drawer__possess-btn"
            :disabled="!possessPrecondition(slot).enabled"
            :title="possessPrecondition(slot).reason || undefined"
            @click="onPossess(slot)"
          >
            附身
          </button>
          <span
            v-if="!possessPrecondition(slot).enabled && possessPrecondition(slot).reason"
            class="act-reason"
            data-testid="party-drawer__possess-reason"
          >{{ possessPrecondition(slot).reason }}</span>
          <template v-if="confirmingLeaveId === slot.identity && leavePrecondition(slot).enabled">
            <button
              type="button"
              class="btn-danger"
              data-testid="party-drawer__leave-confirm"
              @click="confirmLeave(slot)"
            >
              確認離隊
            </button>
            <button
              type="button"
              data-testid="party-drawer__leave-cancel"
              @click="cancelLeave"
            >
              取消
            </button>
          </template>
          <template v-else>
            <button
              type="button"
              data-testid="party-drawer__leave-btn"
              :disabled="!leavePrecondition(slot).enabled"
              :title="leavePrecondition(slot).reason || undefined"
              @click="armLeave(slot)"
            >
              請其離隊
            </button>
          </template>
        </div>
      </div>
    </div>

    <!-- Empty slot row (when party is not full) -->
    <div
      v-if="emptyCount > 0"
      class="compbig compbig--empty"
      data-testid="party-drawer__empty-row"
    >
      <div class="av empty-av">?</div>
      <div class="info">
        <div class="nm empty-nm">空位</div>
        <div class="bondrow empty-rule" data-testid="party-drawer__invite-rule">
          <i>邀請需當地自由 NPC，且羈絆達「親睦」階段</i>
        </div>
        <div class="acts">
          <button
            type="button"
            data-testid="party-drawer__invite-btn"
            :disabled="!inviteResolution.enabled"
            :title="inviteResolution.reason || undefined"
            @click="onInviteCurrentNpc"
          >
            邀請當前 NPC…
          </button>
        </div>
      </div>
    </div>

    <!-- Follow rules card verbatim from reference draft -->
    <div class="quest" data-testid="party-drawer__follow-rules">
      <div class="qh">跟隨規則</div>
      <div class="objs">
        <div class="o">玩家越過出口時自動帶走同室同伴，無時鐘成本、靜音。</div>
        <div class="o">跟丟時顯示「你跟丟了…。」，同伴保留羈絆。</div>
        <div class="o">affinity 低於門檻會自動離隊。</div>
      </div>
    </div>
    </template>
  </section>
</template>

<style scoped>
.party-drawer {
  display: flex;
  flex-direction: column;
  font-family: var(--f-sans);
  color: var(--paper-100);
}

.party-drawer__unavailable {
  font-size: 13px;
  color: var(--paper-500);
  margin: 12px 0;
}

.party-drawer__intro {
  font-size: 12.5px;
  color: var(--paper-500);
  margin: 0 0 14px;
  line-height: 1.5;
}

.compbig {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: var(--ink-820);
  border: 1px solid var(--ink-700);
  border-radius: 11px;
  padding: 12px;
  margin-bottom: 11px;
}

.compbig--empty {
  opacity: 0.85;
}

.compbig .av {
  width: 52px;
  height: 52px;
  flex: none;
  border-radius: 10px;
  background: radial-gradient(60% 70% at 50% 38%, #4a3a2a, #1a150e 82%);
  display: grid;
  place-items: center;
  font-family: var(--f-display);
  font-size: 24px;
  color: var(--gold-400);
  border: 1px solid var(--ink-600);
  overflow: hidden;
}

.empty-av {
  color: var(--paper-500) !important;
}

.av-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.av-glyph {
  line-height: 1;
}

.compbig .info {
  flex: 1;
  min-width: 0;
}

.compbig .nm {
  font-size: 15px;
  color: var(--paper-50);
  font-weight: 600;
}

.empty-nm {
  color: var(--paper-300) !important;
}

.compbig .bondrow {
  font-size: 11px;
  color: var(--gold-400);
  margin: 5px 0 7px;
}

.compbig .bondrow i {
  font-style: normal;
  color: var(--paper-500);
}

.compbig .cbar {
  height: 7px;
  border-radius: 99px;
  background: var(--ink-780);
  overflow: hidden;
}

.compbig .cbar .f {
  height: 100%;
  background: var(--vit-hp);
  border-radius: 99px;
  transition: width var(--motion-base, 150ms) var(--ease-standard, ease);
}

.compbig .meta {
  font-size: 10.5px;
  color: var(--paper-500);
  margin-top: 6px;
  display: flex;
  gap: 12px;
  font-variant-numeric: tabular-nums;
}

.compbig .meta .ko {
  color: var(--seal-400);
  font-weight: 600;
}

.compbig .acts {
  display: flex;
  gap: 6px;
  margin-top: 9px;
}

.compbig .acts button {
  font-size: 11.5px;
  padding: 5px 10px;
  border-radius: 7px;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  color: var(--paper-300);
  cursor: pointer;
  transition: all var(--motion-base, 150ms) var(--ease-standard, ease);
}

.compbig .acts button:hover:not(:disabled) {
  border-color: var(--seal-500);
  color: var(--paper-50);
}

.compbig .acts button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.compbig .acts .btn-danger {
  border-color: var(--seal-500);
  color: var(--seal-400);
}

.compbig .acts .btn-danger:hover:not(:disabled) {
  background: var(--seal-900);
  color: #fff;
}

.quest {
  background: var(--ink-820);
  border: 1px solid rgba(127, 191, 127, 0.4);
  border-radius: 11px;
  padding: 12px 14px;
  margin-top: 4px;
  margin-bottom: 11px;
}

.quest .qh {
  font-size: 13px;
  color: var(--buff, #7fbf7f);
  margin-bottom: 8px;
  font-weight: 600;
}

.quest .objs {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.quest .objs .o {
  font-size: 11.5px;
  color: var(--paper-400);
  line-height: 1.5;
}

.party-drawer__release-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: rgba(142, 68, 173, 0.15);
  border: 1px solid rgba(175, 122, 197, 0.4);
  border-radius: var(--radius-sm, 4px);
  color: #e8daef;
}
.party-drawer__release-text {
  font-size: 13px;
  font-weight: 500;
}
.btn-release {
  background: rgba(142, 68, 173, 0.4);
  border: 1px solid #af7ac5;
  color: #fff;
  padding: 3px 10px;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
}
.btn-release:hover {
  background: rgba(142, 68, 173, 0.7);
}
.btn-possess {
  background: rgba(41, 128, 185, 0.3);
  border: 1px solid rgba(52, 152, 219, 0.6);
  color: #d6eaf8;
  padding: 2px 8px;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  font-size: 12px;
}
.btn-possess:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.act-reason {
  font-size: 11px;
  color: #e74c3c;
  margin-left: 6px;
}
</style>
