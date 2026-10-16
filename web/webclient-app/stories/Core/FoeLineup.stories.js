import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import FoeLineup from "../../components/FoeLineup.vue";
import { combatFormation } from "../../components/combat-formation.js";
import { FOE_PORTRAIT_CATALOG, foeParticipants } from "../fixtures.js";

// FoeLineup (webclient-combat-foes-on-stage design D1-D5;
// webclient-combat-formation design D1/D3): the combat foes standing
// opposite the party. Every active foe up to the line-up's maximum, in
// presenter order. Without a `formation` (the stories above the Formation
// ones) each foe stands at the anchor's right edge at full height; in the
// client the anchor spans the stage in combat and each foe stands at the
// box the combat formation engine gives it. Names and hit points live on the
// figure plates (Core/FigurePlate). Each slot exposes `data-portrait-ref`.
//
// Props: foes (the committed active foes, presenter order), artPanel (the
// committed `art` panel), motionLevel, max (16 minus the drawn party),
// stage (`view.beatStage`: the pre-round foes and each step's gestures
// while a combat round plays), formation (the engine's foe side) and glide.
// Emits `settled` when a leaving foe has faded (decorative art: no
// focusable element, no pointer events, hidden from assistive technology).
//
// The stage frame below reproduces the shell's geometry from the shared
// tokens: the combat scene over the stage box, the fixed bottom band, the
// `actor-right` anchor, and the stage's centre line.

export default {
  title: "Core/FoeLineup",
  component: FoeLineup,
  parameters: { layout: "fullscreen" },
  argTypes: {
    motionLevel: { control: "inline-radio", options: ["full", "reduced", "off"] },
  },
};

const ART_PANEL = {
  schema_version: 2,
  available: true,
  kind: "scene",
  scene: null,
  portrait_catalog: FOE_PORTRAIT_CATALOG,
};

const renderLineup = (args) => ({
  components: { FoeLineup },
  setup: () => ({ args }),
  template: `
    <div style="position:fixed;inset:0;overflow:clip;background:#0b0d10">
      <div style="position:absolute;left:0;right:0;top:var(--header-h);bottom:var(--band-h);background:linear-gradient(0deg,#0b0d10 3%,#0b0d1000 60%),url(/art/scenes/forest_path.webp) center top/cover"></div>
      <div style="position:absolute;inset:0;background:var(--stage-combat-veil)"></div>
      <div aria-hidden="true" style="position:absolute;left:50%;top:var(--header-h);bottom:var(--band-h);border-left:1px dashed rgba(228,200,142,.28)"></div>
      <div
        data-anchor="actor-right"
        style="position:absolute;right:var(--actor-right-inset);bottom:var(--band-h);height:var(--actor-h);aspect-ratio:2/3;z-index:2;pointer-events:none"
      >
        <FoeLineup v-bind="args" />
      </div>
      <div style="position:absolute;left:0;right:0;bottom:0;height:var(--band-h);z-index:5;background:linear-gradient(0deg,#0c0a0e,#141019 70%,var(--panel));border-top:var(--line)"></div>
    </div>`,
});

// One foe at the anchor's right edge, as tall as the player.
export const OneFoe = {
  render: renderLineup,
  args: { foes: foeParticipants(1), artPanel: ART_PANEL, motionLevel: "full" },
};

// Two foes.
export const TwoFoes = {
  render: renderLineup,
  args: { foes: foeParticipants(2), artPanel: ART_PANEL, motionLevel: "full" },
};

// Three foes.
export const ThreeFoes = {
  render: renderLineup,
  args: { foes: foeParticipants(3), artPanel: ART_PANEL, motionLevel: "full" },
};

// The formation (webclient-combat-formation D1): the anchor spans the stage
// and the foes stand at the engine's boxes for this window, opposite a solo
// player, at the shared scale (the dashed lines bound the dead-centre gap).
const renderFormation = (args) => ({
  components: { FoeLineup },
  setup() {
    const size = ref({ width: window.innerWidth, height: window.innerHeight });
    const onResize = () => {
      size.value = { width: window.innerWidth, height: window.innerHeight };
    };
    onMounted(() => window.addEventListener("resize", onResize));
    onBeforeUnmount(() => window.removeEventListener("resize", onResize));
    const formation = computed(() => {
      const style = getComputedStyle(document.documentElement);
      const S = Number(style.getPropertyValue("--ui-scale")) || 1;
      const { width, height } = size.value;
      const band = Math.max(190 * S, Math.min(400 * S, height * 0.2785));
      const header = 48 * S;
      return combatFormation({
        stageWidth: width,
        stageHeight: height,
        uiScale: S,
        bandTop: height - band,
        actorHeight: Math.min(height * 0.62, 680 * S, height - header - band),
        topBandBottom: header,
        vitalsDock: null,
        partyCount: 1,
        foeCount: args.foes.length,
      });
    });
    return { args, formation };
  },
  template: `
    <div style="position:fixed;inset:0;overflow:clip;background:#0b0d10">
      <div style="position:absolute;left:0;right:0;top:var(--header-h);bottom:var(--band-h);background:linear-gradient(0deg,#0b0d10 3%,#0b0d1000 60%),url(/art/scenes/forest_path.webp) center top/cover"></div>
      <div style="position:absolute;inset:0;background:var(--stage-combat-veil)"></div>
      <div aria-hidden="true" :style="{ position: 'absolute', left: formation.gap.left + 'px', width: (formation.gap.right - formation.gap.left) + 'px', top: 'var(--header-h)', bottom: 'var(--band-h)', borderInline: '1px dashed rgba(228,200,142,.28)' }"></div>
      <div data-anchor="actor-right" style="position:absolute;inset:0;z-index:2;pointer-events:none">
        <FoeLineup v-bind="args" :formation="formation.foes" />
      </div>
      <div style="position:absolute;left:0;right:0;bottom:0;height:var(--band-h);z-index:5;background:linear-gradient(0deg,#0c0a0e,#141019 70%,var(--panel));border-top:var(--line)"></div>
    </div>`,
});

// Five foes in one rank, at the scale a solo player shares.
export const FormationFiveFoes = {
  render: renderFormation,
  args: { foes: foeParticipants(5), artPanel: ART_PANEL, motionLevel: "full" },
};

// Fallen foes keep their slots (webclient-combat-defeated-foes D1/D5): the
// second and fourth of five lie collapsed under the broken seal while the
// others stand, at the formation's boxes and scale.
export const FormationSomeDefeated = {
  render: renderFormation,
  args: {
    foes: foeParticipants(5, { 32: { state: "defeated", hp_current: 0 }, 34: { state: "knocked_out", hp_current: 0 } }),
    artPanel: ART_PANEL,
    motionLevel: "full",
  },
};

// Fifteen foes, the participant cap beside a solo player: two ranks, the
// back rank up-stage and half a step toward the centre.
export const FormationFifteenFoes = {
  render: renderFormation,
  args: { foes: foeParticipants(15), artPanel: ART_PANEL, motionLevel: "full" },
};

// A pending catalog entry keeps its own placeholder card and label, with the
// foe's initial in the ring, at the slot's scale.
export const PendingPlaceholder = {
  render: renderLineup,
  args: {
    foes: foeParticipants(2),
    artPanel: {
      ...ART_PANEL,
      portrait_catalog: {
        ...FOE_PORTRAIT_CATALOG,
        32: {
          artwork: {
            ...FOE_PORTRAIT_CATALOG["32"].artwork,
            generation_state: "pending",
            attempts: [],
            terminal: null,
          },
          context: { name: "盜賊頭目", role: "敵方" },
        },
      },
    },
    motionLevel: "full",
  },
};

// A null reference and a reference with no catalog entry both show the
// truthful placeholder: the name's initial and the name, never a stock image.
export const MissingEntry = {
  render: renderLineup,
  args: {
    foes: foeParticipants(3, { 31: { portrait_ref: null }, 33: { portrait_ref: "999" } }),
    artPanel: ART_PANEL,
    motionLevel: "full",
  },
};

// A combat round in progress (webclient-combat-beat-choreography D5): the
// committed roster already lost the assassin, but the row keeps the
// round's pre-round foes while the beats play. The front foe steps in, the
// assassin is hit twice (each hit restarts the shake), then drops out on its own
// defeat beat; the round then ends and the committed foes stand again.
const ROUND_FOES = foeParticipants(3);
const COMMITTED_FOES = foeParticipants(3).filter((foe) => foe.identity !== 33);
// One entry per beat phase: [step, gestures, displayed hit points, defeated].
const ROUND_SCRIPT = [
  [0, { 31: { gesture: "lunge", amount: null } }, { 33: 18 }, []],
  [1, { 33: { gesture: "hit", amount: 10 } }, { 33: 8 }, []],
  [2, { 33: { gesture: "hit", amount: 8 } }, { 33: 0 }, []],
  [3, { 33: { gesture: "defeat", amount: null } }, { 33: 0 }, []],
  [4, {}, { 33: 0 }, ["33"]],
  null,
];

const renderRound = (args) => ({
  components: { FoeLineup },
  setup() {
    const tick = ref(0);
    let timer = null;
    onMounted(() => {
      timer = setInterval(() => {
        tick.value += 1;
      }, 1000);
    });
    onBeforeUnmount(() => clearInterval(timer));
    const entry = computed(() => ROUND_SCRIPT[tick.value % ROUND_SCRIPT.length]);
    const stage = computed(() => {
      const current = entry.value;
      if (!current) {
        return null;
      }
      const [step, gestures, , defeated] = current;
      return {
        key: `story:${Math.floor(tick.value / ROUND_SCRIPT.length)}:${step}`,
        step,
        foes: ROUND_FOES.filter((foe) => !defeated.includes(foe.portrait_ref)),
        defeated,
        gestures,
      };
    });
    return { args, stage, COMMITTED_FOES };
  },
  template: renderLineup(args).template.replace(
    '<FoeLineup v-bind="args" />',
    '<FoeLineup v-bind="args" :foes="COMMITTED_FOES" :stage="stage" />',
  ),
});

export const RoundInProgress = {
  render: renderRound,
  args: { artPanel: ART_PANEL, motionLevel: "full" },
};
