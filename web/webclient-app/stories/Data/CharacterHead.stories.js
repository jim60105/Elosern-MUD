import { h } from "vue";
import CharacterHead from "../../components/CharacterHead.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  CHARACTER_PANEL_TITLED_SAMPLE,
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_SAMPLE,
  STATUS_PANEL_TITLED_SAMPLE,
} from "../fixtures.js";

// CharacterHead (H2, webclient-hud-02-status-islands, design D2/D3): the
// head-card island with deterministic offline args — badge power levels,
// guild joined vs 未加入公會, disguise on/off, a zero wallet, and a long
// name that must ellipsize. The per-rank-band stories are retired with the
// magic-rank ladder (magic-power-static-rename).

function withMagicPower(character, power) {
  return {
    ...character,
    traits: character.traits.map((row) =>
      row.key === "magic_power" ? { ...row, current: power } : row,
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

// Low and high magic-power badges (the numeric badge is a plain value; the
// retired rank ladder shows nowhere on the card).
export const PowerLow = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: withMagicPower(CHARACTER_PANEL_SAMPLE, 5),
  },
};

export const PowerHigh = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: withMagicPower(CHARACTER_PANEL_SAMPLE, 90),
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

// title-system D6: with a composed full title on the committed status panel,
// the head card addresses the player by 稱號　異名 while the glyph portrait
// keeps deriving from the character's own name.
export const TitledFullTitle = {
  render: renderHead,
  args: {
    status: STATUS_PANEL_TITLED_SAMPLE,
    character: CHARACTER_PANEL_TITLED_SAMPLE,
  },
};
