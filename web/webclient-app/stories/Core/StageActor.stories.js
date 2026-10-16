import { onBeforeUnmount, onMounted, ref } from "vue";
import StageActor from "../../components/StageActor.vue";
import {
  artworkDescriptor,
  artworkResource,
  artworkTerminal,
} from "../fixtures/art_panels.js";

// Every position is a committed descriptor judged against its committed panel
// (change unified-portrait-image-contract).
const PANEL = { schema_version: 3, available: true };

const descriptor = (subject, url, faceRect, overrides = {}) =>
  artworkDescriptor({
    subject_id: subject,
    generation_subject: subject,
    attempts: [
      {
        type: "image",
        source_id: `portrait.default:${subject}`,
        rank: 30,
        resource: artworkResource({
          resource_id: url,
          url,
          geometry: {
            image_size: null,
            face_rect: faceRect,
            stage: { scale: 1, x: 0, y: 0 },
            aspect_ratio: "3:4",
          },
        }),
      },
    ],
    terminal: artworkTerminal(),
    ...overrides,
  });

// StageActor (webclient-dialogue-stage-actors design D1): one standing
// portrait on the stage. It wraps ReferenceArtwork and adds the side it
// stands on (`data-side`, which mirrors the soft edge mask) and the static
// speaking state (`data-speaking`; the listener is dimmed through the shared
// `--actor-dim` token). With no entry it draws the name's initial and the
// name, never a stock image. Deterministic offline args: the committed
// built-in fallbacks under `/art/defaults/` stand in for generated art.
//
// Props: artwork (the canonical descriptor of this figure position, or null),
// panel (the committed panel it is judged against), hasReference, name, side
// ("left" | "right"), dimmed, motionLevel, the combat
// beat gesture (gesture: null | "lunge" | "hit" | "defeat", gestureKey,
// floatAmount), and the fallen look (fallen: null | "defeated" | "down",
// fallInstant). Emits nothing (decorative
// art: no focusable element, no pointer events).

export default {
  title: "Core/StageActor",
  component: StageActor,
  parameters: { layout: "centered" },
  argTypes: {
    side: { control: "inline-radio", options: ["left", "right"] },
    dimmed: { control: "boolean" },
    motionLevel: { control: "inline-radio", options: ["full", "reduced", "off"] },
    gesture: { control: "inline-radio", options: [null, "lunge", "hit", "defeat"] },
    fallen: { control: "inline-radio", options: [null, "defeated", "down"] },
  },
};

// A stage-sized anchor over a scene-like ground, so the edge masks and the
// dim read the way they do on the stage.
const renderActor = (args) => ({
  components: { StageActor },
  setup: () => ({ args }),
  template:
    '<div style="width:420px;height:630px;padding:0;background:radial-gradient(120% 90% at 50% 20%,#3b4250,#15171b 70%)">' +
    '<StageActor v-bind="args" /></div>',
});

const PLAYER_PORTRAIT = descriptor("char_1", "/art/defaults/man.webp", {
  x: 0.25,
  y: 0.06,
  w: 0.5,
  h: 0.5,
});

const HOST_ENTRY = descriptor("npc_41", "/art/defaults/elder.webp", {
  x: 0.3,
  y: 0.1,
  w: 0.4,
  h: 0.4,
});

// The host's generation is still running: no real candidate, no terminal.
const HOST_PENDING_ENTRY = descriptor("npc_41", "/art/defaults/elder.webp", null, {
  generation_state: "pending",
  attempts: [],
  terminal: null,
});

// The player in `actor-left`, lit (exploration, or the player speaking).
export const Player = {
  render: renderActor,
  args: { artwork: PLAYER_PORTRAIT, panel: PANEL, name: "艾莉亞", side: "left", dimmed: false },
};

// The dialogue host in `actor-right`: the catalog entry's image.
export const HostImage = {
  render: renderActor,
  args: { artwork: HOST_ENTRY, panel: PANEL, name: "灰婆婆", side: "right", dimmed: false },
};

// The host's entry is still generating: the entry's own placeholder card.
export const HostPendingPlaceholder = {
  render: renderActor,
  args: { artwork: HOST_PENDING_ENTRY, panel: PANEL, name: "灰婆婆", side: "right", dimmed: false },
};

// No catalog entry (`portrait_ref` null): the name's initial and the name.
export const HostMissingEntry = {
  render: renderActor,
  args: {
    artwork: null,
    panel: PANEL,
    hasReference: false,
    name: "合成‧旅人",
    side: "right",
    dimmed: false,
  },
};

export const Failed = {
  render: renderActor,
  args: {
    artwork: { ...HOST_PENDING_ENTRY, generation_state: "failed" },
    panel: PANEL,
    name: "灰婆婆",
  },
};
export const LoadFailed = {
  render: renderActor,
  args: {
    artwork: descriptor("npc_41", "/art/does-not-exist.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 }),
    panel: PANEL,
    name: "灰婆婆",
  },
};
// Deliberately opaque input: preserve its supplied background, never guess a cutout.
export const Opaque = {
  render: renderActor,
  args: {
    artwork: descriptor(
      "npc_41",
      `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="600"><rect width="400" height="600" fill="#686a70"/><circle cx="200" cy="95" r="50" fill="#202027"/><path d="M150 155h100l45 440H105Z" fill="#202027"/></svg>')}`,
      { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
    ),
    panel: PANEL,
    name: "合成‧旅人",
  },
};

// The speaker: full brightness, `data-speaking="true"`.
export const Speaking = {
  render: renderActor,
  args: { artwork: HOST_ENTRY, panel: PANEL, name: "灰婆婆", side: "right", dimmed: false },
};

// The listener: `--actor-dim` brightness, `data-speaking="false"`.
export const Dimmed = {
  render: renderActor,
  args: { artwork: PLAYER_PORTRAIT, panel: PANEL, name: "艾莉亞", side: "left", dimmed: true },
};

// An appearance change (webclient-scene-transitions, design D5): every few
// seconds the portrait source changes — another image, then the pending
// placeholder card — and the new figure crossfades in above the old one.
// In between, the speaking state flips, so the dim eases.
const APPEARANCES = [
  PLAYER_PORTRAIT,
  descriptor("char_1", "/art/defaults/woman.webp", { x: 0.25, y: 0.06, w: 0.5, h: 0.5 }),
  { ...PLAYER_PORTRAIT, generation_state: "pending", attempts: [], terminal: null },
];

export const AppearanceChange = {
  render: () => ({
    components: { StageActor },
    setup() {
      const tick = ref(0);
      let timer = null;
      onMounted(() => {
        timer = setInterval(() => {
          tick.value += 1;
        }, 1800);
      });
      onBeforeUnmount(() => clearInterval(timer));
      return { tick, APPEARANCES, PANEL };
    },
    template:
      '<div style="width:420px;height:630px;padding:0;background:radial-gradient(120% 90% at 50% 20%,#3b4250,#15171b 70%)">' +
      '<StageActor :artwork="APPEARANCES[Math.floor(tick / 2) % APPEARANCES.length]" :panel="PANEL" name="艾莉亞" side="left" :dimmed="tick % 2 === 1" /></div>',
  }),
};

// A stage-triple change on the SAME url (gallery-stage-transform D5): the
// figure re-scales and slides on its own style, never a crossfade — the
// crossfade key ignores `stage`, so every frame below is the same mounted
// image. Cycles identity -> child 0.6 -> translated child -> back.
const stageTriple = (stage) => {
  const descriptor = PLAYER_PORTRAIT;
  descriptor.attempts[0].resource.geometry.stage = stage;
  return descriptor;
};
const STAGE_CYCLES = [
  PLAYER_PORTRAIT,
  stageTriple({ scale: 0.6, x: 0, y: 0 }),
  stageTriple({ scale: 0.6, x: -0.25, y: 0 }),
];

export const StageTransformChange = {
  render: () => ({
    components: { StageActor },
    setup() {
      const tick = ref(0);
      let timer = null;
      onMounted(() => {
        timer = setInterval(() => {
          tick.value += 1;
        }, 1800);
      });
      onBeforeUnmount(() => clearInterval(timer));
      return { tick, STAGE_CYCLES, PANEL };
    },
    template:
      '<div style="width:420px;height:630px;padding:0;background:radial-gradient(120% 90% at 50% 20%,#3b4250,#15171b 70%)">' +
      '<StageActor :artwork="STAGE_CYCLES[tick % STAGE_CYCLES.length]" :panel="PANEL" name="艾莉亞" side="left" /></div>',
  }),
};

// The combat beat gestures (webclient-combat-beat-choreography design D4):
// the figure replays its gesture every beat, keyed by the step so each
// replay restarts the animation, with a rest beat in between. Durations and
// distances are the motion tokens, so the toolbar's reduced-motion
// preference shows the reduced level (only the defeat fade survives).
const renderBeatLoop = ({ gesture, floatAmount, ...args }) => ({
  components: { StageActor },
  setup() {
    const step = ref(0);
    let timer = null;
    onMounted(() => {
      timer = setInterval(() => {
        step.value += 1;
      }, 900);
    });
    onBeforeUnmount(() => clearInterval(timer));
    return { args, step, gesture, floatAmount };
  },
  template:
    '<div style="width:420px;height:630px;padding:0;background:radial-gradient(120% 90% at 50% 20%,#3b4250,#15171b 70%)">' +
    '<StageActor v-bind="args" :gesture="step % 2 === 0 ? gesture : null" :gesture-key="`story:${step}`"' +
    ' :float-amount="step % 2 === 0 ? floatAmount : null" /></div>',
});

// The first beat of an action: the player steps toward the stage centre and
// back (right, from `actor-left`).
export const BeatLunge = {
  render: renderBeatLoop,
  args: { artwork: PLAYER_PORTRAIT, panel: PANEL, name: "艾莉亞", side: "left", dimmed: false, gesture: "lunge", floatAmount: null },
};

// A damage beat on a foe: the figure shakes with a brief flash while the
// damage number rises from it and fades.
export const BeatHit = {
  render: renderBeatLoop,
  args: { artwork: HOST_ENTRY, panel: PANEL, name: "灰婆婆", side: "right", dimmed: false, gesture: "hit", floatAmount: 12 },
};

// A foe's defeat beat (webclient-combat-defeated-foes D4): the figure
// collapses into its defeated look in place and the seal presses in after
// it; the rest beat brings it back up for the replay.
const renderFallLoop = ({ fallen, ...args }) => ({
  components: { StageActor },
  setup() {
    const step = ref(0);
    let timer = null;
    onMounted(() => {
      timer = setInterval(() => {
        step.value += 1;
      }, 1600);
    });
    onBeforeUnmount(() => clearInterval(timer));
    return { args, step, fallen };
  },
  template:
    '<div style="width:420px;height:630px;padding:0;background:radial-gradient(120% 90% at 50% 20%,#3b4250,#15171b 70%)">' +
    '<StageActor v-bind="args" :fallen="step % 2 === 1 ? fallen : null"' +
    ' :gesture="step % 2 === 1 ? \'defeat\' : null" :gesture-key="`story:${step}`" /></div>',
});

export const BeatDefeat = {
  render: renderFallLoop,
  args: { artwork: HOST_ENTRY, panel: PANEL, name: "灰婆婆", side: "right", dimmed: false, fallen: "defeated" },
};

// The fallen looks (webclient-combat-defeated-foes design D1/D2), at rest:
// a defeated foe collapses to 80% about its base, greyed and darkened at
// 0.8 opacity with a broken seal over its chest; the look sits on the figure
// wrapper, so a portrait, a placeholder card and failed art take it alike.
export const DefeatedPortrait = {
  render: renderActor,
  args: { artwork: HOST_ENTRY, panel: PANEL, name: "灰婆婆", side: "right", fallen: "defeated" },
};
export const DefeatedPlaceholder = {
  render: renderActor,
  args: { artwork: null, panel: PANEL, hasReference: false, name: "哥布林", side: "right", fallen: "defeated" },
};
export const DefeatedFailedArt = {
  render: renderActor,
  args: { artwork: { ...HOST_PENDING_ENTRY, generation_state: "failed" }, panel: PANEL, name: "灰婆婆", side: "right", fallen: "defeated" },
};
// A downed ally: kneeling at 92%, half desaturated, no seal; its plate says 倒地.
export const DownedAlly = {
  render: renderActor,
  args: { artwork: HOST_ENTRY, panel: PANEL, name: "艾莉亞", side: "left", fallen: "down" },
};

// The four reads side by side: a standing figure, a dialogue listener
// (dimmed: colour, pose and opacity kept, no mark), a downed ally (the
// kneel) and a defeated foe (the collapse and the seal). Every fallen pair
// differs by shape and mark, never by brightness alone; the plates add the
// words.
export const FallenVsDim = {
  render: () => ({
    components: { StageActor },
    setup: () => ({ PANEL, PLAYER_PORTRAIT, HOST_ENTRY }),
    template:
      '<div style="display:flex;gap:28px;align-items:flex-end;padding:24px;background:radial-gradient(120% 90% at 50% 20%,#3b4250,#15171b 70%)">' +
      [
        ["站立", '<StageActor :artwork="HOST_ENTRY" :panel="PANEL" name="灰婆婆" side="right" />'],
        ["聆聽（變暗）", '<StageActor :artwork="HOST_ENTRY" :panel="PANEL" name="灰婆婆" side="left" dimmed />'],
        ["倒地", '<StageActor :artwork="HOST_ENTRY" :panel="PANEL" name="灰婆婆" side="left" fallen="down" />'],
        ["已擊破", '<StageActor :artwork="HOST_ENTRY" :panel="PANEL" name="灰婆婆" side="right" fallen="defeated" />'],
      ]
        .map(
          ([label, actor]) =>
            '<figure style="margin:0;display:grid;gap:10px;justify-items:center">' +
            `<div style="width:220px;height:330px">${actor}</div>` +
            `<figcaption style="font:16px/1 var(--f-sans);color:var(--paper-300)">${label}</figcaption></figure>`,
        )
        .join("") +
      "</div>",
  }),
};

// The defeat at `reduced` (webclient-combat-defeated-foes D4): the pose lands
// at once with no travel; only the tone and the seal fade, within 150ms.
export const DefeatedReducedMotion = {
  render: (args) => ({
    ...renderFallLoop(args),
    setup() {
      const inner = renderFallLoop(args).setup();
      const previous = document.documentElement.dataset.motion;
      onMounted(() => {
        document.documentElement.dataset.motion = "reduced";
      });
      onBeforeUnmount(() => {
        if (previous === undefined) delete document.documentElement.dataset.motion;
        else document.documentElement.dataset.motion = previous;
      });
      return inner;
    },
  }),
  args: { artwork: HOST_ENTRY, panel: PANEL, name: "灰婆婆", side: "right", dimmed: false, fallen: "defeated", motionLevel: "reduced" },
};
