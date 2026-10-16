import { onBeforeUnmount, ref } from "vue";
import FigurePlate from "../../components/FigurePlate.vue";
import { PLATE_CONDITIONS as C } from "../fixtures/combat_stage.js";

// FigurePlate (webclient-combat-formation design D4): the glance plate each
// combat figure other than the controlled one carries in the stage's
// `plates` layer, at the plate slot the formation engine gives it.
//
// Props: name, token, showToken (only while two drawn participants share
// the name), side (`party` | `foes`), hpCurrent / hpMaximum (the displayed
// playback value while a round plays), form (`full` 112×52px·S |
// `compact` 72×36px·S), box (the engine's slot in stage px; absent here, so
// the plate lays out in flow at its form's size), target / acting (the
// non-colour cues), conditions (the participant's committed rows: glyphs on
// the last line, details in a tooltip on hover or focus — try it), closeSignal
// and stageX (the plates group's order). At or below 25% hit points the
// current value turns crit and a 危險 tag joins the plate
// (webclient-combat-figure-plates). Only the glyphs take pointer events;
// the plate is a tabindex=-1 stop of the stage's plates group.
//
// Each plate stands over a scene and a figure's head, as on the stage, so
// the feathered ground and the brass crown are reviewed over art.

export default {
  title: "Core/FigurePlate",
  component: FigurePlate,
  parameters: { layout: "fullscreen" },
  argTypes: {
    side: { control: "inline-radio", options: ["party", "foes"] },
    form: { control: "inline-radio", options: ["full", "compact"] },
  },
};

const render = (args) => ({
  components: { FigurePlate },
  setup: () => ({ args }),
  template: `
    <div style="position:relative;height:320px;display:grid;place-items:center;background:linear-gradient(0deg,#0b0d10 6%,#0b0d1000 70%),url(/art/scenes/forest_path.webp) center/cover">
      <div style="position:relative;display:flex;flex-direction:column;align-items:center">
        <FigurePlate v-bind="args" />
        <img src="/art/defaults/monster_anon.webp" alt="" style="height:200px;margin-top:4px;object-fit:cover;object-position:50% 0" />
      </div>
    </div>`,
});

export const FullFoe = { render, args: { name: "灰袍盜賊", token: "e1", side: "foes", hpCurrent: 18, hpMaximum: 30, form: "full" } };
export const FullAlly = { render, args: { name: "蕾娜", token: "a2", side: "party", hpCurrent: 42, hpMaximum: 120, form: "full" } };
export const CompactFoe = { render, args: { name: "哥布林", token: "e6", side: "foes", hpCurrent: 24, hpMaximum: 24, form: "compact" } };
export const CompactAlly = { render, args: { name: "幽", token: "a3", side: "party", hpCurrent: 144, hpMaximum: 160, form: "compact" } };
export const Damaged = { render, args: { name: "盜賊頭目", token: "e2", side: "foes", hpCurrent: 40, hpMaximum: 90, form: "full" } };
export const LongName = {
  render,
  args: { name: "灰袍盜賊與北境巡防隊長的漫長稱號", token: "e1", side: "foes", hpCurrent: 999, hpMaximum: 999, form: "full" },
};
export const RepeatedName = { render, args: { name: "哥布林", token: "e7", showToken: true, side: "foes", hpCurrent: 9, hpMaximum: 24, form: "full" } };
export const FocusedTarget = { render, args: { name: "蒙面刺客", token: "e3", side: "foes", hpCurrent: 18, hpMaximum: 50, form: "full", target: true } };
export const Acting = { render, args: { name: "盜賊頭目", token: "e2", side: "foes", hpCurrent: 90, hpMaximum: 90, form: "full", acting: true } };

// webclient-combat-figure-plates: every plate state.
export const FullHp = { render, args: { name: "蕾娜", token: "a2", side: "party", hpCurrent: 120, hpMaximum: 120, form: "full" } };
export const LowHpAlarm = { render, args: { name: "蕾娜", token: "a2", side: "party", hpCurrent: 24, hpMaximum: 120, form: "full", conditions: [C.bleed] } };
export const WithConditions = { render, args: { name: "灰袍盜賊", token: "e1", side: "foes", hpCurrent: 18, hpMaximum: 30, form: "full", conditions: [C.poison, C.bless] } };
export const ConditionOverflow = {
  render,
  args: { name: "盜賊頭目", token: "e2", side: "foes", hpCurrent: 60, hpMaximum: 90, form: "full", conditions: [C.poison, C.haste, C.fog, C.stun, C.slow, C.bless, C.bleed, C.fear] },
};
export const LongNameLowWithConditions = {
  render,
  args: { name: "灰袍盜賊與北境巡防隊長的漫長稱號", token: "e1", showToken: true, side: "foes", hpCurrent: 9, hpMaximum: 90, form: "full", conditions: [C.stun, C.poison, C.slow, C.fear] },
};
export const Compact = { render, args: { name: "哥布林", token: "e6", side: "foes", hpCurrent: 14, hpMaximum: 24, form: "compact" } };
export const CompactWithConditions = { render, args: { name: "哥布林", token: "e6", side: "foes", hpCurrent: 14, hpMaximum: 24, form: "compact", conditions: [C.bless, C.poison, C.stun] } };
export const CompactLowHpFold = { render, args: { name: "哥布林", token: "e6", side: "foes", hpCurrent: 4, hpMaximum: 24, form: "compact", conditions: [C.bless, C.poison, C.stun] } };
export const CompactLowHpNoConditions = { render, args: { name: "哥布林", token: "e6", side: "foes", hpCurrent: 4, hpMaximum: 24, form: "compact" } };
// A round's beats drain the displayed value (`displayHp`) page by page: the
// stroke trails each drop, and the alarm rises as it crosses 25%.
// Fallen plates (webclient-combat-defeated-foes D1): the name stays, the
// stroke empties to a dashed outline and the glyph and the word replace the
// numbers; a compact plate moves them to its glyph line.
export const DefeatedFoe = { render, args: { name: "灰袍盜賊", token: "e1", side: "foes", hpCurrent: 0, hpMaximum: 30, form: "full", fallen: "defeated" } };
export const DownedAlly = { render, args: { name: "蕾娜", token: "a2", side: "party", hpCurrent: 0, hpMaximum: 120, form: "full", fallen: "down", conditions: [C.bleed] } };
export const CompactDefeated = { render, args: { name: "哥布林", token: "e6", side: "foes", hpCurrent: 0, hpMaximum: 24, form: "compact", fallen: "defeated" } };
export const CompactDowned = { render, args: { name: "幽", token: "a3", side: "party", hpCurrent: 0, hpMaximum: 160, form: "compact", fallen: "down" } };

export const PlaybackDrain = {
  args: { name: "灰袍盜賊", token: "e1", side: "foes", hpMaximum: 60, form: "full", conditions: [C.poison] },
  render: (args) => ({
    components: { FigurePlate },
    setup() {
      const hp = ref(60);
      const pages = [60, 44, 31, 15, 9, 60];
      let index = 0;
      const timer = setInterval(() => {
        index = (index + 1) % pages.length;
        hp.value = pages[index];
      }, 1200);
      onBeforeUnmount(() => clearInterval(timer));
      return { args, hp };
    },
    template: `
      <div style="position:relative;height:320px;display:grid;place-items:center;background:linear-gradient(0deg,#0b0d10 6%,#0b0d1000 70%),url(/art/scenes/forest_path.webp) center/cover">
        <div style="position:relative;display:flex;flex-direction:column;align-items:center">
          <FigurePlate v-bind="args" :hp-current="hp" />
          <img src="/art/defaults/monster_anon.webp" alt="" style="height:200px;margin-top:4px;object-fit:cover;object-position:50% 0" />
        </div>
      </div>`,
  }),
};
