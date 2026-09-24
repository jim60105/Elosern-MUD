<script setup>
// TopBar (H1, webclient-hud-01-shell-and-scene; MC5
// multichar-05-topbar-switcher-ui; webclient-avg-place-card-top-bar design
// D1): the slim 48px top band. The top-left brand element carries the game
// name 「伊洛瑟恩」 (the `webclient-login-gate` brand surface set) beside the
// ELOSERN wordmark on one row; the top-right cluster hosts the possession
// banner, the CharacterSwitcher pill, and the meta pill, which states only
// the connection state (the ok-green dot paired with a text label — never
// color alone). Location and world time live in the stage's place card.
import CharacterSwitcher from "./CharacterSwitcher.vue";

defineProps({
  connected: { type: Boolean, default: false },
  rosterAvailable: { type: Boolean, default: false },
  rosterCharacters: { type: Array, default: () => [] },
  rosterCanCreate: { type: Boolean, default: false },
  rosterSwitchLocked: { type: Boolean, default: false },
  rosterLockReason: { type: String, default: null },
  locked: { type: Boolean, default: false },
  epoch: { type: [Number, String], default: null },
  possessionBanner: { type: Object, default: null },
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
    <span class="topbar-wordmark">ELOSERN</span>
    <span class="topbar-tagline">伊洛瑟恩</span>
  </div>
  <div class="topbar-right">
    <div
      v-if="possessionBanner && possessionBanner.available"
      class="topbar-possession-banner"
      data-testid="topbar-possession-banner"
    >
      你透過{{ possessionBanner.host_name }}的雙眼行動
    </div>
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
      <span class="meta-conn" data-testid="connection-state">
        {{ connected ? "● 已連線" : "○ 未連線" }}
      </span>
    </div>
  </div>
</template>

<style>
/* The top band: the brand at the top-left corner, the meta pill at the
   top-right corner. The stage anchors begin below the band's lower edge,
   so nothing overlaps it. */
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

.topbar-possession-banner {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  background: rgba(142, 68, 173, 0.25);
  border: 1px solid rgba(175, 122, 197, 0.6);
  border-radius: var(--radius-sm, 4px);
  color: #e8daef;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.5px;
  pointer-events: none;
  user-select: none;
}
</style>
