import AvatarArtwork from "../../components/AvatarArtwork.vue";
import {
  artworkDescriptor,
  artworkResource,
  artworkTerminal,
} from "../fixtures/art_panels.js";

// The ONE shared small-avatar renderer (change unified-avatar-rendering):
// roster/switcher thumbnails, presence medallions, party rows and combat
// participant rows all read one descriptor through one real-only lifecycle.
// Every story below is deterministic and offline; the fallback states are
// painted from the descriptor's own facts, never from an invented bitmap.
const PANEL = { schema_version: 3, available: true };

// One real candidate with its own face rectangle. The nonidentity stage triple
// is deliberate: an avatar crop must ignore it.
function avatar(url, faceRect, subject = "port_hero") {
  return artworkDescriptor({
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
            stage: { scale: 1.4, x: -0.2, y: 0.1 },
            aspect_ratio: "3:4",
          },
        }),
      },
    ],
    terminal: artworkTerminal(),
  });
}

export default {
  title: "Core/AvatarArtwork",
  component: AvatarArtwork,
  parameters: { layout: "centered" },
};

const render = (args) => ({
  components: { AvatarArtwork },
  setup: () => ({ args }),
  template: '<AvatarArtwork v-bind="args" style="width:52px;height:52px;background:#121519" />',
});

// The real portrait with its own zoom crop: the small avatar's normal state.
export const RealPortrait = {
  render,
  args: {
    artwork: avatar("/art/defaults/man.webp", { x: 0.25, y: 0.06, w: 0.5, h: 0.5 }),
    panel: PANEL,
    name: "艾莉亞",
  },
};

// The combat participant row's policy: the same descriptor, recenters-only.
export const RecenterCrop = {
  render,
  args: {
    crop: "recenter",
    artwork: avatar("/art/defaults/man.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 }),
    panel: PANEL,
    name: "小美",
  },
};

// No real candidate yet: the first grapheme of the trimmed name stands, with
// no error styling (an unfinished generation is expected, not broken).
export const IdentityInitial = {
  render,
  args: {
    artwork: artworkDescriptor({ generation_state: "pending", attempts: [], terminal: null }),
    panel: PANEL,
    name: "蕾娜",
  },
};

// A whole grapheme cluster: a ZWJ emoji sequence is one initial, never a split.
export const GraphemeInitial = {
  render,
  args: {
    artwork: artworkDescriptor({ generation_state: "pending", attempts: [], terminal: null }),
    panel: PANEL,
    name: "\u{1F469}\u200D\u{1F4BB}技師",
  },
};

// An empty displayed name: the neutral text symbol instead of a blank tile.
export const EmptyName = {
  render,
  args: {
    artwork: artworkDescriptor({ generation_state: "pending", attempts: [], terminal: null }),
    panel: PANEL,
    name: "   ",
  },
};

// A reached fault: the compact corner marker keeps the bounded explanation
// (keyboard-reachable; never hover-only and never color-only).
export const FailureMarker = {
  render,
  args: {
    artwork: artworkDescriptor({
      generation_state: "failed",
      attempts: [
        { type: "fault", source_id: "portrait.default:9", rank: 10, reason: "generation_failed" },
      ],
      terminal: null,
    }),
    panel: PANEL,
    name: "凱爾",
  },
};

// A required panel that could not supply its data: the shared availability
// sentence, not a broken-image claim.
export const PanelUnavailable = {
  render,
  args: {
    artwork: artworkDescriptor(),
    panel: { schema_version: 3, available: false },
    name: "凱爾",
  },
};

// A hosted avatar (the switcher pill/rows and the presence rail): the
// explanation renders for the OWNING control's `aria-describedby`, so the
// compact mark stays inert and no second focusable control is nested.
export const HostedExplanation = {
  render: (args) => ({
    components: { AvatarArtwork },
    setup: () => ({ args }),
    template:
      '<button type="button" aria-describedby="avatar-story-explanation" ' +
      'style="width:52px;height:52px;padding:0;background:#121519">' +
      '<AvatarArtwork v-bind="args" /></button>',
  }),
  args: {
    artwork: artworkDescriptor({
      attempts: [
        { type: "fault", source_id: "portrait.default:9", rank: 10, reason: "image_load_failed" },
      ],
      terminal: null,
    }),
    panel: PANEL,
    name: "凱爾",
    failureTextId: "avatar-story-explanation",
  },
};
