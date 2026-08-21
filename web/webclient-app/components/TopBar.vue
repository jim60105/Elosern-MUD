<script setup>
// Top bar (the header surface): the game title, the current location and the
// server clock from the status/server-time slice, and the transport
// connection state. The connection state pairs a glyph dot with a text label
// plus a state border on the non-connected side, so it is never conveyed by
// color alone. The `.header-conn` hook and the connected/disconnected state
// classes are the preserved DOM contract (Phase-0 audit §2.3).
defineProps({
  locationLabel: { type: String, default: null },
  timeLabel: { type: String, default: null },
  connected: { type: Boolean, default: false },
});
</script>

<template>
  <header
    class="elosern elosern-header"
    :class="connected ? 'connected' : 'disconnected'"
    data-testid="topbar"
  >
    <div class="header-title" data-testid="topbar-title">霧落</div>
    <div class="header-meta">
      <span class="header-location" data-testid="topbar-location">
        {{ locationLabel || "位置：--" }}
      </span>
      <span class="header-clock" data-testid="topbar-clock">
        {{ timeLabel || "時間：--" }}
      </span>
      <span class="header-conn" data-testid="connection-state">
        {{ connected ? "● 已連線" : "○ 未連線" }}
      </span>
    </div>
  </header>
</template>

<style>
.elosern-header {
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
  height: 56px;
  padding: 0 var(--sp-5);
  border-bottom: var(--line);
  background: var(--panel);
}

.elosern-header .header-title {
  font-family: var(--f-display);
  font-size: 20px;
  letter-spacing: 0.18em;
  color: var(--paper-50);
}

.elosern-header .header-meta {
  display: flex;
  align-items: center;
  gap: var(--sp-5);
  font-size: var(--text-sm);
  color: var(--paper-500);
}

.elosern-header .header-location {
  color: var(--paper-300);
}

.elosern-header .header-clock {
  font-family: var(--f-mono);
}

.elosern-header .header-conn {
  font-family: var(--f-mono);
}

.elosern-header.connected .header-conn {
  color: var(--ok);
}

.elosern-header.disconnected .header-conn {
  color: var(--warn);
  border: 1px dashed var(--warn);
  border-radius: var(--radius-sm);
  padding: 1px var(--sp-2);
}
</style>
