import ReferenceArtwork from "../../components/ReferenceArtwork.vue";

export default {
  title: "Core/ReferenceArtwork",
  component: ReferenceArtwork,
  parameters: { layout: "centered" },
};

const renderArtwork = (args) => ({
  components: { ReferenceArtwork },
  setup: () => ({ args }),
  template: '<ReferenceArtwork v-bind="args" style="width:340px;height:640px;background:#121519" />',
});

export const CharacterPortrait = {
  render: renderArtwork,
  args: {
    portrait: {
      subject_key: "port_hero",
      status: "done",
      url: "/art/defaults/man.webp",
      aspect_ratio: "3:4",
      alt: "主角的肖像",
      placeholder: null,
      face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
    },
  },
};

export const ElderPortrait = {
  render: renderArtwork,
  args: {
    portrait: {
      subject_key: "port_elder",
      status: "done",
      url: "/art/defaults/elder.webp",
      aspect_ratio: "3:4",
      alt: "長者的肖像",
      placeholder: null,
      face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
    },
  },
};

export const MonsterPortrait = {
  render: renderArtwork,
  args: {
    portrait: {
      subject_key: "monster_anon",
      status: "done",
      url: "/art/defaults/monster_anon.webp",
      aspect_ratio: "3:4",
      alt: "野獸的肖像",
      placeholder: null,
      face_rect: { x: 0.2, y: 0.15, w: 0.6, h: 0.5 },
    },
  },
};

// Stage-transform states (gallery-stage-transform D3/D5): the same full-figure
// asset rendered on the stage branch at the bottom-center anchor, so the
// offline showcase documents how the persisted triple reads at scale.
const renderStage = (args) => ({
  components: { ReferenceArtwork },
  setup: () => ({ args }),
  template:
    '<div style="width:340px;height:453px;background:radial-gradient(120% 90% at 50% 18%,#3b4250,#15171b 72%)">' +
    '<ReferenceArtwork v-bind="args" /></div>',
});

const stagePortrait = (stage) => ({
  subject_key: "port_hero",
  status: "done",
  url: "/art/defaults/man.webp",
  aspect_ratio: "3:4",
  alt: "主角的全身像",
  placeholder: null,
  face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
  stage,
});

export const StageIdentity = {
  render: renderStage,
  args: { stage: true, portrait: stagePortrait({ scale: 1, x: 0, y: 0 }) },
};

export const StageNullDefault = {
  render: renderStage,
  args: { stage: true, portrait: stagePortrait(null) },
};

export const StageChildScale = {
  render: renderStage,
  args: { stage: true, portrait: stagePortrait({ scale: 0.6, x: 0, y: 0 }) },
};

export const StageOffsets = {
  render: renderStage,
  args: { stage: true, portrait: stagePortrait({ scale: 0.6, x: 0.15, y: -0.1 }) },
};

export const StageEnlargedOverflow = {
  render: renderStage,
  args: { stage: true, portrait: stagePortrait({ scale: 2, x: 0.3, y: 0 }) },
};
