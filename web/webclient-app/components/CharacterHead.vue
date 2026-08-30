<script setup>
// CharacterHead (H2, webclient-hud-02-status-islands, design D2/D3/D11):
// the left stack's head-card island. It renders exactly the identity the
// committed payloads carry — a glyph portrait tile (the player is never a
// present focusable subject of their own exploration catalog, so no
// portrait image exists and none is invented), a numeric magic_power badge,
// the display name, the guild rank/merit line, the wallet, and the disguise
// marker. The retired magic-rank ladder is not reconstructed client-side:
// no magic-derived rank word appears in any form (magic-power-static-rename;
// the title-system change line owns title display). The composed full title
// (`status.actor.full_title`) renders as the addressed name when present;
// a pre-onboarding character (empty title) falls back to the plain name
// (title-system D6 name fallback). No race, subrace,
// class, or faction line: no such field exists in the `status` or
// `character` payload, and none is rendered (not dimmed, not "未知", not
// a placeholder). The wallet is the HUD's single persistent surface.
import { computed } from "vue";
import { formatCopper, portraitGlyph } from "./character-identity.js";

const props = defineProps({
  status: { type: Object, required: true },
  character: { type: Object, required: true },
});

const actorName = computed(() => props.status?.actor?.name ?? "");
// The composed full title (fixed　epithet) or the plain name fallback.
const displayName = computed(() => props.status?.actor?.full_title || actorName.value);
const portrait = computed(() => portraitGlyph(actorName.value));

// The magic_power trait row's current value is the only bounded numeric
// progression the payload carries; it is a display-only badge, always from
// the true trait, never from the disguised displayed value (design D2).
const magicPower = computed(() => {
  const rows = props.character?.traits ?? [];
  return rows.find((row) => row.key === "magic_power")?.current ?? null;
});

const guild = computed(() => props.character?.guild ?? null);
const wallet = computed(() => Math.max(0, Number(props.character?.wallet ?? 0)));
const disguiseActive = computed(() => props.status?.disguise_active === true);
</script>

<template>
  <div class="hud character-head" data-testid="character-head">
    <div class="portrait" data-testid="character-head__portrait">
      <span class="mono" data-testid="character-head__glyph">{{ portrait }}</span>
      <span v-if="magicPower !== null" class="lv" data-testid="character-head__badge">
        {{ magicPower }}
      </span>
    </div>
    <div class="meta">
      <p class="name" data-testid="character-head__name">{{ displayName }}</p>
      <p class="rank" data-testid="character-head__rank">
        <span class="rank-guild"
          >公會 {{ guild?.rank ?? "未加入公會" }} · 功績 {{ guild?.merit ?? 0 }}</span
        >
      </p>
      <p class="sub" data-testid="character-head__wallet">錢包 {{ formatCopper(wallet) }} 銅</p>
      <p v-if="disguiseActive" class="disguise" data-testid="character-head__disguise">目前有偽裝</p>
    </div>
  </div>
</template>

<style scoped>
/* The shared island chrome (design D1/D2.1), expressed through the shared
   design tokens only. */
.hud {
  background: var(--panel);
  backdrop-filter: blur(9px);
  -webkit-backdrop-filter: blur(9px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.character-head {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 12px;
  font-family: var(--f-sans);
}

.portrait {
  position: relative;
  width: 58px;
  height: 58px;
  flex: none;
  border-radius: 11px;
  overflow: hidden;
  background: radial-gradient(60% 70% at 50% 38%, #4a3a2a, #1a150e 80%);
  display: grid;
  place-items: center;
  border: 1px solid var(--ink-600);
}

.mono {
  font-family: var(--f-display);
  font-size: 28px;
  color: var(--gold-400);
  line-height: 1;
}

.lv {
  position: absolute;
  right: 0;
  bottom: 0;
  font-family: var(--f-mono);
  font-size: 10px;
  font-weight: 700;
  color: var(--ink-950);
  background: var(--gold-500);
  border-top-left-radius: 6px;
  padding: 1px 5px;
}

.meta {
  min-width: 0;
  flex: 1;
}

.name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--paper-50);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rank {
  margin: 1px 0 0;
  font-size: 11.5px;
  color: var(--seal-400);
}

.rank-guild {
  color: var(--gold-400);
  font-size: 10.5px;
  margin-left: 7px;
}

.sub {
  margin: 1px 0 0;
  font-size: 10.5px;
  color: var(--paper-500);
  font-family: var(--f-mono);
}

.disguise {
  margin: 2px 0 0;
  font-size: 10.5px;
  color: var(--warn);
}
</style>
