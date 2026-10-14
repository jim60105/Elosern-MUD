import { h } from "vue";
import ParticipantFrame from "../../components/ParticipantFrame.vue";
import {
  artworkDescriptor,
  artworkResource,
  artworkTerminal,
} from "../fixtures/art_panels.js";

// One catalog value per participant row: exactly `{artwork, context}`.
function entry(subject, url, faceRect, generation = "done") {
  return {
    artwork: artworkDescriptor({
      subject_id: subject,
      generation_subject: subject,
      generation_state: generation,
      attempts: url
        ? [
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
          ]
        : [],
      terminal: url ? artworkTerminal() : null,
    }),
    context: { name: subject, role: "敵方" },
  };
}

// ParticipantFrame (H3 webclient-hud-03-action-dock, task 6.8): the combat
// participant frame — 我方 / 敵方 groups, the token/name/HP numerals, the
// explicit state markers, and the catalog-resolved portraits. Deterministic
// offline args for the showcase.

const ART_PANEL = {
  schema_version: 3,
  available: true,
  portrait_catalog: {
    p1: entry("port_hero", "/art/defaults/man.webp", { x: 0.25, y: 0.06, w: 0.5, h: 0.5 }),
    e1: entry("port_goblin", "/art/defaults/monster_anon.webp", { x: 0.35, y: 0.12, w: 0.4, h: 0.4 }),
    e2: entry("port_ogre", null, null, "pending"),
  },
};

const renderFrame = (args) => ({
  render: () =>
    h("div", { style: "background: var(--ink-900); padding: 8px; border-radius: 8px;" }, [
      h(ParticipantFrame, args),
    ]),
});

export default {
  title: "Data/ParticipantFrame",
  component: ParticipantFrame,
};

// Party + foes with all states and portrait refs (task 6.8).
export const PartyAndFoes = {
  render: renderFrame,
  args: {
    participants: [
      { identity: 1, token: "P1", display_name: "林楓", team: "party", state: "active", hp_current: 80, hp_maximum: 100, portrait_ref: "p1" },
      { identity: 2, token: "E1", display_name: "哥布林", team: "foes", state: "active", hp_current: 40, hp_maximum: 60, portrait_ref: "e1" },
      { identity: 3, token: "E2", display_name: "巨魔", team: "foes", state: "active", hp_current: 120, hp_maximum: 200, portrait_ref: "e2" },
    ],
    artPanel: ART_PANEL,
  },
};

// A fled / knocked-out / defeated participant (the explicit text markers,
// task 6.1/6.8).
export const FledKnockedOutDefeated = {
  render: renderFrame,
  args: {
    participants: [
      { identity: 2, token: "E1", display_name: "哥布林", team: "foes", state: "fled", hp_current: 30, hp_maximum: 60, portrait_ref: "e1" },
      { identity: 1, token: "P1", display_name: "林楓", team: "party", state: "knocked_out", hp_current: 0, hp_maximum: 100, portrait_ref: "p1" },
      { identity: 3, token: "E2", display_name: "巨魔", team: "foes", state: "defeated", hp_current: 0, hp_maximum: 200, portrait_ref: "e2" },
    ],
    artPanel: ART_PANEL,
  },
};

// A `null` portrait ref renders no card (task 6.2/6.8).
export const NullPortraitRef = {
  render: renderFrame,
  args: {
    participants: [
      { identity: 1, token: "P1", display_name: "林楓", team: "party", state: "active", hp_current: 100, hp_maximum: 100, portrait_ref: null },
    ],
    artPanel: ART_PANEL,
  },
};

// An unavailable art panel renders no thumbnail, even with a non-null ref.
export const UnavailableArtPanel = {
  render: renderFrame,
  args: {
    participants: [
      { identity: 2, token: "E1", display_name: "哥布林", team: "foes", state: "active", hp_current: 40, hp_maximum: 60, portrait_ref: "e1" },
    ],
    artPanel: { schema_version: 1, available: false, reason: { code: "art_unavailable", message: "藝術面板目前無法顯示" }, portrait_catalog: null },
  },
};

// A playing combat round's displayed hit points (webclient-combat-beat-queue
// D7): the rows the map names state the beat's `hp_after` instead of their
// committed `hp_current`; every other row and field is unchanged.
export const DisplayedHp = {
  render: renderFrame,
  args: {
    participants: [
      { identity: 1, token: "P1", display_name: "林楓", team: "party", state: "active", hp_current: 80, hp_maximum: 100, portrait_ref: "p1" },
      { identity: 2, token: "E1", display_name: "哥布林", team: "foes", state: "active", hp_current: 40, hp_maximum: 60, portrait_ref: "e1" },
      { identity: 3, token: "E2", display_name: "巨魔", team: "foes", state: "active", hp_current: 120, hp_maximum: 200, portrait_ref: "e2" },
    ],
    artPanel: ART_PANEL,
    displayHp: { e1: 18 },
  },
};
