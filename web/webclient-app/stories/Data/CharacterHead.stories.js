import { h } from "vue";
import CharacterHead from "../../components/CharacterHead.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../fixtures.js";

// CharacterHead (H2, webclient-hud-02-status-islands, design D2/D3): the
// head-card island with deterministic offline args — each rank band, guild
// joined vs 未加入公會, disguise on/off, a zero wallet, and a long name
// that must ellipsize.

function withMagicLevel(character, level) {
  return {
    ...character,
    traits: character.traits.map((row) =>
      row.key === "magic_level" ? { ...row, current: level } : row,
    ),
  };
}

const renderHead = (args) => ({
  render: () =>
    h("div", { style: "width: 262px;" }, [h(CharacterHead, args)]),
});

export default {
  title: "Data/CharacterHead",
  component: CharacterHead,
};

// One story per magic rank band (the client-side display table's five bands,
// pinned by the Vitest boundary tests).
export const RankApprentice = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: withMagicLevel(CHARACTER_PANEL_SAMPLE, 5),
  },
};

export const RankSorcerer = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: withMagicLevel(CHARACTER_PANEL_SAMPLE, 20),
  },
};

export const RankMaster = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: withMagicLevel(CHARACTER_PANEL_SAMPLE, 45),
  },
};

export const RankSage = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: withMagicLevel(CHARACTER_PANEL_SAMPLE, 80),
  },
};

export const RankSovereign = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: withMagicLevel(CHARACTER_PANEL_SAMPLE, 95),
  },
};

export const GuildNotJoined = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: {
      ...CHARACTER_PANEL_SAMPLE,
      guild: { rank: null, merit: 0 },
    },
  },
};

export const DisguiseOn = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: CHARACTER_PANEL_SAMPLE,
  },
};

export const DisguiseOff = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_COMBAT_SAMPLE,
    character: CHARACTER_PANEL_SAMPLE,
  },
};

export const ZeroWallet = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: { ...CHARACTER_PANEL_SAMPLE, wallet: 0 },
  },
};

// A display name long enough to ellipsize inside the 262px card.
export const LongNameEllipsize = {
  render: renderHead,
  args: {
    status: {
      ...STATUS_PANEL_SAMPLE,
      actor: { ...STATUS_PANEL_SAMPLE.actor, name: "艾倫·灰誓·拾荒者同盟·灰裔血脈" },
    },
    character: CHARACTER_PANEL_SAMPLE,
  },
};
