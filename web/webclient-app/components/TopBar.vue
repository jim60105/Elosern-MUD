<script setup>
// TopBar (H1, webclient-hud-01-shell-and-scene, design D5; MC5 multichar-05-topbar-switcher-ui):
// the header is
// split into the top-left brand element (the game name 「伊洛瑟恩」, preserving
// the `webclient-login-gate` brand surface set) and the top-right cluster
// hosting the CharacterSwitcher dropdown pill and the meta pill
// (location · world date/time · connection state, with the ok-green dot paired
// with a text label — never color alone). The wallet is deliberately not added
// here (it belongs to H2's island stack).
//
// All elements are anchored to the stage's top band; the HUD island anchors
// start below them at top:64px (design D10).
import CharacterSwitcher from "./CharacterSwitcher.vue";

defineProps({
  locationLabel: { type: String, default: null },
  timeLabel: { type: String, default: null },
  connected: { type: Boolean, default: false },
  rosterAvailable: { type: Boolean, default: false },
  rosterCharacters: { type: Array, default: () => [] },
  rosterCanCreate: { type: Boolean, default: false },
  rosterSwitchLocked: { type: Boolean, default: false },
  rosterLockReason: { type: String, default: null },
  locked: { type: Boolean, default: false },
  epoch: { type: [Number, String], default: null },
});

defineEmits({
  "switch-character": (characterId) => typeof characterId === "number",
  "create-character": () => true,
});
</script>

<template>
  <div
    class="topbar-brand"
    data-testid="topbar-title"
    :class="connected ? 'connected' : 'disconnected'"
  >
    伊洛瑟恩
  </div>
  <div class="topbar-right">
    <CharacterSwitcher
      :available="rosterAvailable"
      :characters="rosterCharacters"
      :can-create="rosterCanCreate"
      :switch-locked="rosterSwitchLocked"
      :lock-reason="rosterLockReason"
      :locked="locked || !connected"
      :epoch="epoch"
      @switch-character="$emit('switch-character', $event)"
      @create-character="$emit('create-character')"
    />
    <div
      class="topbar-meta"
      data-testid="topbar"
      :class="connected ? 'connected' : 'disconnected'"
    >
      <span class="meta-loc" data-testid="topbar-location">
        {{ locationLabel || "位置：--" }}
      </span>
      <span class="sep" aria-hidden="true"></span>
      <span class="meta-clock" data-testid="topbar-clock">
        {{ timeLabel || "時間：--" }}
      </span>
      <span class="sep" aria-hidden="true"></span>
      <span class="meta-conn" data-testid="connection-state">
        {{ connected ? "● 已連線" : "○ 未連線" }}
      </span>
    </div>
  </div>
</template>

<style>
/* The top band: the brand at the top-left corner, the meta pill at the
   top-right corner. The HUD island anchors begin at top:64px (design D10),
   so this band is bounded above them and nothing overlaps. */
.topbar-brand {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 4;
  font-family: var(--f-display);
  font-size: 20px;
  letter-spacing: 0.18em;
  color: var(--paper-50);
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 6px var(--sp-4);
}

.topbar-right {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 4;
  display: flex;
  gap: 8px;
  align-items: center;
  max-width: calc(100vw - 160px);
}

.topbar-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: var(--line);
  border-radius: 999px;
  padding: 6px 13px;
  box-shadow: var(--shadow);
  font-size: 11.5px;
  color: var(--paper-300);
  white-space: nowrap;
  flex-shrink: 0;
}

.topbar-meta .meta-loc {
  color: var(--gold-400);
  font-weight: 600;
}

.topbar-meta .sep {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--paper-700);
}

.topbar-meta .meta-clock {
  font-family: var(--f-mono);
}

.topbar-meta .meta-conn {
  font-family: var(--f-mono);
}

.topbar-meta.connected .meta-conn {
  color: var(--ok);
}

.topbar-meta.disconnected .meta-conn {
  color: var(--warn);
  border: 1px dashed var(--warn);
  border-radius: var(--radius-sm);
  padding: 1px var(--sp-2);
}
</style>
