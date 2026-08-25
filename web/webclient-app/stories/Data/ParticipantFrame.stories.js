import { h } from "vue";
import ParticipantFrame from "../../components/ParticipantFrame.vue";

// ParticipantFrame (H3 webclient-hud-03-action-dock, task 6.8): the combat
// participant frame — 我方 / 敵方 groups, the token/name/HP numerals, the
// explicit state markers, and the catalog-resolved portraits. Deterministic
// offline args for the showcase.

const ART_PANEL = {
  schema_version: 1,
  available: true,
  portrait_catalog: {
    p1: { subject_key: "port_hero", status: "done", url: "/art/portraits/port_hero.png", alt: "主角的肖像", placeholder: null },
    e1: { subject_key: "port_goblin", status: "done", url: "/art/portraits/port_goblin.png", alt: "哥布林的肖像", placeholder: null },
    e2: { subject_key: "port_ogre", status: "pending", url: null, alt: "巨魔的肖像", placeholder: { kind: "missing", label: "肖像圖像尚未生成" } },
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

// An unavailable art panel: the portrait catalog is absent, so a non-null
// portrait ref renders the catalog's placeholder card (task 6.2/6.8).
export const UnavailableArtPanel = {
  render: renderFrame,
  args: {
    participants: [
      { identity: 2, token: "E1", display_name: "哥布林", team: "foes", state: "active", hp_current: 40, hp_maximum: 60, portrait_ref: "e1" },
    ],
    artPanel: { schema_version: 1, available: false, reason: { code: "art_unavailable", message: "藝術面板目前無法顯示" }, portrait_catalog: null },
  },
};
