import { h } from "vue";
import HudDrawer from "../../components/HudDrawer.vue";
import PartyDrawer from "../../components/PartyDrawer.vue";
import {
  PARTY_PANEL_EMPTY_SAMPLE,
  PARTY_PANEL_SAMPLE,
  PARTY_PANEL_FULL_SAMPLE,
  PARTY_COMBAT_PARTICIPANTS_SAMPLE,
  PARTY_INTERACT_TARGETS_SAMPLE,
  ART_PANEL_SAMPLE,
} from "../fixtures.js";

// PartyDrawer (webclient-align-05-party-hud):
// the 同伴 · 隊伍 drawer body, shown inside the shared right-anchored HudDrawer chrome.
// Deterministic and offline.

export default {
  title: "Overlays/PartyDrawer",
  component: PartyDrawer,
};

function renderDrawer(args) {
  const slots = args.slots || [];
  return {
    render: () =>
      h(
        "div",
        {
          style:
            "position: relative; width: 100%; height: 600px; background: var(--ink-950, #0d0a12); overflow: hidden;",
        },
        [
          h(
            HudDrawer,
            {
              open: true,
              title: "同伴 · 隊伍",
              subtitle: `${slots.length} / 4`,
              drawerKey: "party",
              icon: "party",
              onClose: () => {},
            },
            {
              default: () =>
                h(PartyDrawer, {
                  slots,
                  combatParticipants: args.combatParticipants || [],
                  artPanel: args.artPanel || null,
                  interactTargets: args.interactTargets || [],
                  mode: args.mode || "exploration",
                  onAction: () => {},
                  onClose: () => {},
                }),
            },
          ),
        ],
      ),
  };
}

export const TwoCompanions = {
  render: renderDrawer,
  args: {
    slots: PARTY_PANEL_SAMPLE.slots,
    combatParticipants: PARTY_COMBAT_PARTICIPANTS_SAMPLE,
    artPanel: ART_PANEL_SAMPLE,
    interactTargets: PARTY_INTERACT_TARGETS_SAMPLE,
    mode: "exploration",
  },
};

export const PossessionAndRelease = {
  render: renderDrawer,
  args: {
    slots: PARTY_PANEL_SAMPLE.slots,
    combatParticipants: [],
    artPanel: ART_PANEL_SAMPLE,
    interactTargets: PARTY_INTERACT_TARGETS_SAMPLE,
    mode: "exploration",
    releaseAffordance: {
      action_id: "explore.possess_release",
      label: "歸位",
      params: { npc_id: 101 },
      enabled: true,
    },
    affordances: [
      {
        action_id: "explore.possess",
        label: "附身",
        params: { npc_id: 101 },
        enabled: true,
      },
      {
        action_id: "explore.possess",
        label: "附身",
        params: { npc_id: 102 },
        enabled: false,
        disabled_reason: { code: "in_combat", message: "戰鬥中無法附身。" },
      },
    ],
  },
};

export const EmptyParty = {
  render: renderDrawer,
  args: {
    slots: PARTY_PANEL_EMPTY_SAMPLE.slots,
    combatParticipants: [],
    artPanel: null,
    interactTargets: PARTY_INTERACT_TARGETS_SAMPLE,
    mode: "exploration",
  },
};

export const FullParty = {
  render: renderDrawer,
  args: {
    slots: PARTY_PANEL_FULL_SAMPLE.slots,
    combatParticipants: PARTY_COMBAT_PARTICIPANTS_SAMPLE,
    artPanel: null,
    interactTargets: [],
    mode: "exploration",
  },
};

export const CombatMode = {
  render: renderDrawer,
  args: {
    slots: PARTY_PANEL_SAMPLE.slots,
    combatParticipants: PARTY_COMBAT_PARTICIPANTS_SAMPLE,
    artPanel: null,
    interactTargets: [],
    mode: "combat",
  },
};
