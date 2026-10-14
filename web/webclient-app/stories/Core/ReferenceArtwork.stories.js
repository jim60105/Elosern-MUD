import ReferenceArtwork from "../../components/ReferenceArtwork.vue";
import {
  artworkDescriptor,
  artworkResource,
  artworkTerminal,
} from "../fixtures/art_panels.js";

// Every position is a committed descriptor judged against its committed panel
// (change unified-portrait-image-contract).
const PANEL = { schema_version: 3, available: true };

// One framed portrait descriptor: a resolved candidate with its own geometry.
const framed = (subject, url, faceRect) =>
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
  });

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
    artwork: framed("port_hero", "/art/defaults/man.webp", { x: 0.25, y: 0.06, w: 0.5, h: 0.5 }),
    panel: PANEL,
    name: "主角的肖像",
  },
};

export const ElderPortrait = {
  render: renderArtwork,
  args: {
    artwork: framed("port_elder", "/art/defaults/elder.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 }),
    panel: PANEL,
    name: "長者的肖像",
  },
};

export const MonsterPortrait = {
  render: renderArtwork,
  args: {
    artwork: framed("monster_anon", "/art/defaults/monster_anon.webp", { x: 0.2, y: 0.15, w: 0.6, h: 0.5 }),
    panel: PANEL,
    name: "野獸的肖像",
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

const stagePortrait = (stage) => {
  const descriptor = framed("port_hero", "/art/defaults/man.webp", { x: 0.25, y: 0.06, w: 0.5, h: 0.5 });
  descriptor.attempts[0].resource.geometry.stage = stage;
  return descriptor;
};

export const StageIdentity = {
  render: renderStage,
  args: { stage: true, panel: PANEL, name: "主角的全身像", artwork: stagePortrait({ scale: 1, x: 0, y: 0 }) },
};

export const StageNullDefault = {
  render: renderStage,
  args: { stage: true, panel: PANEL, name: "主角的全身像", artwork: stagePortrait(null) },
};

export const StageChildScale = {
  render: renderStage,
  args: { stage: true, panel: PANEL, name: "主角的全身像", artwork: stagePortrait({ scale: 0.6, x: 0, y: 0 }) },
};

export const StageOffsets = {
  render: renderStage,
  args: { stage: true, panel: PANEL, name: "主角的全身像", artwork: stagePortrait({ scale: 0.6, x: 0.15, y: -0.1 }) },
};

export const StageEnlargedOverflow = {
  render: renderStage,
  args: { stage: true, panel: PANEL, name: "主角的全身像", artwork: stagePortrait({ scale: 2, x: 0.3, y: 0 }) },
};
