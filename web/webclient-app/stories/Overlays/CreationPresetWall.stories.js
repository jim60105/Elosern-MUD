import { h } from "vue";
import CreationPresetWall from "../../components/CreationPresetWall.vue";
import { CREATION_PANEL_SAMPLE } from "../fixtures.js";
import { CREATION_WALL_PRESETS } from "../fixtures/creation_wall.js";

// CreationPresetWall (creation-preset-card-wall; design §5): the preset card
// wall on its own, framed at the overlay body's height. Opening a card by
// pointer, ← / → or its ordinal digit only moves the local expansion; the
// expanded card's 以〈名字〉啟程 (or Enter) is the single deliberate choose,
// logged to the Actions panel instead of being sent anywhere.
const RACES = Object.fromEntries(CREATION_PANEL_SAMPLE.custom.races.map((race) => [race.key, race.display_name_zh]));
const raceDisplayName = (key) => RACES[key] ?? key;

const frame = (args) => ({
  render: () =>
    h(
      "div",
      {
        class: "elosern",
        style:
          "position:absolute;inset:0;display:flex;flex-direction:column;padding:16px 32px;box-sizing:border-box;background:var(--ink-950)",
      },
      [h(CreationPresetWall, { raceDisplayName, ...args })],
    ),
});

export default {
  title: "Overlays/CreationPresetWall",
  component: CreationPresetWall,
  render: frame,
  argTypes: { onChoose: { action: "choose" } },
};

// Eight cards with figures; the first card opens on entry (no draft). The
// sixth card's image is missing, so it shows the alpha-terminal silhouette.
export const Default = {
  args: { presets: CREATION_WALL_PRESETS, draftPresetKey: null },
};

// A saved preset draft opens its own card and carries the 目前草稿 marker.
export const DraftRestored = {
  args: { presets: CREATION_WALL_PRESETS, draftPresetKey: CREATION_WALL_PRESETS[2].key },
};

// A mutation in flight: browsing stays live, the primary action is held.
export const ChooseHeld = {
  args: { presets: CREATION_WALL_PRESETS, draftPresetKey: null, disabled: true },
};

// Cards whose descriptors carry no official image: every figure is the
// shared loader's alpha-terminal silhouette, never an invented URL.
export const SilhouetteOnly = {
  args: { presets: CREATION_PANEL_SAMPLE.presets, draftPresetKey: null },
};

// A single supplied card: it is expanded and the arrows clamp in place.
export const SingleCard = {
  args: { presets: CREATION_WALL_PRESETS.slice(0, 1), draftPresetKey: null },
};
