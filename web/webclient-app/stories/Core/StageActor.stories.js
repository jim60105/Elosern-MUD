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
// null), name, side ("left" | "right"), dimmed. Emits nothing (decorative
// art: no focusable element, no pointer events).

export default {
  title: "Core/StageActor",
  component: StageActor,
  parameters: { layout: "centered" },
  argTypes: {
    side: { control: "inline-radio", options: ["left", "right"] },
    dimmed: { control: "boolean" },
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
  args: { portrait: null, name: "合成·旅人", side: "right", dimmed: false },
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
