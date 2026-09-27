import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import FoeLineup from "../../components/FoeLineup.vue";
import { FOE_PORTRAIT_CATALOG, foeParticipants } from "../fixtures.js";

// FoeLineup (webclient-combat-foes-on-stage design D1-D5): the combat foes
// standing opposite the player in `actor-right`. At most three active foes,
// in presenter order, as a depth-staged row that grows leftward: the first
// foe stands in front at the anchor's right edge, each later foe stands
// behind the one before it and smaller. Each foe carries a decorative
// hit-point gauge with a trailing bar on the stage floor; the numbers stay in
// the participant frame. Each slot exposes `data-portrait-ref`.
//
// Props: foes (the committed active foes, presenter order), artPanel (the
// committed `art` panel), motionLevel, max (the cap; stories only), and,
// while a combat round plays (webclient-combat-beat-choreography D5), stage
// (`view.beatStage`: the pre-round foes and each step's gestures) and
// displayHp (`view.displayHp`). Emits
// nothing (decorative art: no focusable element, no pointer events,
// hidden from assistive technology).
//
// The stage frame below reproduces the shell's geometry from the shared
// tokens: the combat scene over the stage box, the fixed bottom band, the
// `actor-right` anchor, and the stage's centre line, so the row's reach reads
// the way it does in the client.

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
      <div style="position:absolute;left:0;right:0;top:var(--header-h);bottom:var(--band-h);background:linear-gradient(0deg,#0b0d10 3%,#0b0d1000 60%),url(/art/showcase/sample-forest.webp) center top/cover"></div>
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

// One foe stands where the host stands, as tall as the player.
export const OneFoe = {
  render: renderLineup,
  args: { foes: foeParticipants(1), artPanel: ART_PANEL, motionLevel: "full" },
};

// Two foes: the second steps behind the first, toward the centre.
export const TwoFoes = {
  render: renderLineup,
  args: { foes: foeParticipants(2), artPanel: ART_PANEL, motionLevel: "full" },
};

// Three foes: the fullest row, still right of the stage's centre line; the
// third is wounded, so its gauge shows the damage.
export const ThreeFoes = {
  render: renderLineup,
  args: { foes: foeParticipants(3), artPanel: ART_PANEL, motionLevel: "full" },
};

// Five active foes: only the first three stand on the stage; the participant
// frame lists all five (no "+N" plate).
export const FiveFoesCapped = {
  render: renderLineup,
  args: { foes: foeParticipants(5), artPanel: ART_PANEL, motionLevel: "full" },
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
          subject_key: "npc_32",
          status: "pending",
          url: null,
          aspect_ratio: null,
          alt: "盜賊頭目的肖像",
          placeholder: { kind: "missing", label: "肖像生成中" },
          face_rect: null,
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
// assassin is hit twice (each hit restarts the shake, the gauge and its
// trailing bar follow the displayed hit points), then drops out on its own
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
    const displayHp = computed(() => (entry.value ? entry.value[2] : null));
    return { args, stage, displayHp, COMMITTED_FOES };
  },
  template: renderLineup(args).template.replace(
    '<FoeLineup v-bind="args" />',
    '<FoeLineup v-bind="args" :foes="COMMITTED_FOES" :stage="stage" :display-hp="displayHp" />',
  ),
});

export const RoundInProgress = {
  render: renderRound,
  args: { artPanel: ART_PANEL, motionLevel: "full" },
};
