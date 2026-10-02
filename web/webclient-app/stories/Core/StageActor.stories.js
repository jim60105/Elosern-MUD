import { onBeforeUnmount, onMounted, ref } from "vue";
import StageActor from "../../components/StageActor.vue";

// StageActor (webclient-dialogue-stage-actors design D1): one standing
// portrait on the stage. It wraps ReferenceArtwork and adds the side it
// stands on (`data-side`, which mirrors the soft edge mask) and the static
// speaking state (`data-speaking`; the listener is dimmed through the shared
// `--actor-dim` token). With no entry it draws the name's initial and the
// name, never a stock image. Deterministic offline args: the committed
// built-in fallbacks under `/art/defaults/` stand in for generated art.
//
// Props: portrait (a roster portrait or an `art` panel catalog entry, or
// null), name, side ("left" | "right"), dimmed, motionLevel, and the combat
// beat gesture (gesture: null | "lunge" | "hit" | "defeat", gestureKey,
// floatAmount). Emits nothing (decorative
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

const PLAYER_PORTRAIT = {
  subject_key: "char_1",
  status: "done",
  url: "/art/defaults/man.webp",
  aspect_ratio: "3:4",
  alt: "艾莉亞的肖像",
  placeholder: null,
  face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
};

const HOST_ENTRY = {
  subject_key: "npc_41",
  status: "done",
  url: "/art/defaults/elder.webp",
  aspect_ratio: "3:4",
  alt: "灰婆婆的肖像",
  placeholder: null,
  face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
  context: { name: "灰婆婆", role: "對話對象" },
};

const HOST_PENDING_ENTRY = {
  subject_key: "npc_41",
  status: "pending",
  url: null,
  aspect_ratio: null,
  alt: "灰婆婆的肖像",
  placeholder: { kind: "missing", label: "肖像圖像尚未生成" },
  face_rect: null,
  context: { name: "灰婆婆", role: "對話對象" },
};

// The player in `actor-left`, lit (exploration, or the player speaking).
export const Player = {
  render: renderActor,
  args: { portrait: PLAYER_PORTRAIT, side: "left", dimmed: false },
};

// The dialogue host in `actor-right`: the catalog entry's image.
export const HostImage = {
  render: renderActor,
  args: { portrait: HOST_ENTRY, name: "灰婆婆", side: "right", dimmed: false },
};

// The host's entry is still generating: the entry's own placeholder card.
export const HostPendingPlaceholder = {
  render: renderActor,
  args: { portrait: HOST_PENDING_ENTRY, name: "灰婆婆", side: "right", dimmed: false },
};

// No catalog entry (`portrait_ref` null): the name's initial and the name.
export const HostMissingEntry = {
  render: renderActor,
  args: { portrait: null, name: "合成‧旅人", side: "right", dimmed: false },
};

export const Failed = {
  render: renderActor,
  args: { portrait: { ...HOST_PENDING_ENTRY, status: "failed" }, name: "灰婆婆" },
};
export const LoadFailed = {
  render: renderActor,
  args: { portrait: { ...HOST_ENTRY, url: "/art/does-not-exist.webp" }, name: "灰婆婆" },
};
// Deliberately opaque input: preserve its supplied background, never guess a cutout.
export const Opaque = {
  render: renderActor,
  args: {
    portrait: { ...HOST_ENTRY, url: `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="600"><rect width="400" height="600" fill="#686a70"/><circle cx="200" cy="95" r="50" fill="#202027"/><path d="M150 155h100l45 440H105Z" fill="#202027"/></svg>')}` },
    name: "合成‧旅人",
  },
};

// The speaker: full brightness, `data-speaking="true"`.
export const Speaking = {
  render: renderActor,
  args: { portrait: HOST_ENTRY, name: "灰婆婆", side: "right", dimmed: false },
};

// The listener: `--actor-dim` brightness, `data-speaking="false"`.
export const Dimmed = {
  render: renderActor,
  args: { portrait: PLAYER_PORTRAIT, side: "left", dimmed: true },
};

// An appearance change (webclient-scene-transitions, design D5): every few
// seconds the portrait source changes — another image, then the pending
// placeholder card — and the new figure crossfades in above the old one.
// In between, the speaking state flips, so the dim eases.
const APPEARANCES = [
  PLAYER_PORTRAIT,
  { ...PLAYER_PORTRAIT, url: "/art/defaults/woman.webp", alt: "艾莉亞的新肖像" },
  { ...PLAYER_PORTRAIT, status: "pending", url: null, placeholder: { kind: "missing", label: "肖像生成中" } },
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
      return { tick, APPEARANCES };
    },
    template:
      '<div style="width:420px;height:630px;padding:0;background:radial-gradient(120% 90% at 50% 20%,#3b4250,#15171b 70%)">' +
      '<StageActor :portrait="APPEARANCES[Math.floor(tick / 2) % APPEARANCES.length]" name="艾莉亞" side="left" :dimmed="tick % 2 === 1" /></div>',
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
  args: { portrait: PLAYER_PORTRAIT, side: "left", dimmed: false, gesture: "lunge", floatAmount: null },
};

// A damage beat on a foe: the figure shakes with a brief flash while the
// damage number rises from it and fades.
export const BeatHit = {
  render: renderBeatLoop,
  args: { portrait: HOST_ENTRY, name: "灰婆婆", side: "right", dimmed: false, gesture: "hit", floatAmount: 12 },
};

// A foe's defeat beat: the figure fades and sinks out (it stays gone until
// the rest beat brings it back for the replay).
export const BeatDefeat = {
  render: renderBeatLoop,
  args: { portrait: HOST_ENTRY, name: "灰婆婆", side: "right", dimmed: false, gesture: "defeat", floatAmount: null },
};
