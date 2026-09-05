import { h } from "vue";
import CharacterSwitcher from "../../components/CharacterSwitcher.vue";
import { ROSTER_CHARACTERS_SAMPLE } from "../fixtures.js";

// CharacterSwitcher (MC5, multichar-05-topbar-switcher-ui):
// The TopBar character switcher dropdown. Deterministic offline showcase stories
// covering collapsed, expanded, combat-locked, capacity-reached, pending-sibling,
// long-name truncation, and disconnected states.

function stage(children) {
  return h(
    "div",
    {
      style:
        "position: relative; width: 100%; height: 420px; background: var(--ink-950); padding: 24px; display: flex; justify-content: flex-end;",
    },
    children,
  );
}

function renderSwitcher(args) {
  return {
    render: () =>
      stage([
        h(CharacterSwitcher, {
          available: args.available ?? true,
          characters: args.characters ?? ROSTER_CHARACTERS_SAMPLE,
          canCreate: args.canCreate ?? true,
          switchLocked: args.switchLocked ?? false,
          lockReason: args.lockReason ?? null,
          locked: args.locked ?? false,
          initialExpanded: args.initialExpanded ?? false,
        }),
      ]),
  };
}

export default {
  title: "Core/CharacterSwitcher",
  component: CharacterSwitcher,
  parameters: {
    docs: {
      description: {
        component:
          "The TopBar character switcher pill and popover dropdown. " +
          "Collapsed: current portrait thumbnail and name. " +
          "Expanded: roster characters in payload order, pending badge, current marker, " +
          "shared lock note when combat-locked, and trailing confirmation-gated create row.",
      },
    },
  },
};

export const Collapsed = {
  render: renderSwitcher,
  args: {
    available: true,
    characters: ROSTER_CHARACTERS_SAMPLE,
    canCreate: true,
    switchLocked: false,
    locked: false,
    initialExpanded: false,
  },
};

export const Expanded = {
  render: renderSwitcher,
  args: {
    available: true,
    characters: ROSTER_CHARACTERS_SAMPLE,
    canCreate: true,
    switchLocked: false,
    locked: false,
    initialExpanded: true,
  },
};

export const CombatLocked = {
  render: renderSwitcher,
  args: {
    available: true,
    characters: ROSTER_CHARACTERS_SAMPLE,
    canCreate: true,
    switchLocked: true,
    lockReason: "戰鬥中無法切換角色",
    locked: false,
    initialExpanded: true,
  },
};

export const CapacityReached = {
  render: renderSwitcher,
  args: {
    available: true,
    characters: ROSTER_CHARACTERS_SAMPLE,
    canCreate: false,
    switchLocked: false,
    locked: false,
    initialExpanded: true,
  },
};

export const PendingSibling = {
  render: renderSwitcher,
  args: {
    available: true,
    characters: ROSTER_CHARACTERS_SAMPLE,
    canCreate: true,
    switchLocked: false,
    locked: false,
    initialExpanded: true,
  },
};

export const LongNameTruncation = {
  render: renderSwitcher,
  args: {
    available: true,
    characters: [
      {
        identity: 1,
        name: "艾莉亞·馮·阿爾托利亞·潘德拉貢·卡美洛之光",
        current: true,
        pending: false,
        portrait: null,
      },
      {
        identity: 2,
        name: "雷恩",
        current: false,
        pending: false,
        portrait: null,
      },
    ],
    canCreate: true,
    switchLocked: false,
    locked: false,
    initialExpanded: true,
  },
};

export const Disconnected = {
  render: renderSwitcher,
  args: {
    available: true,
    characters: ROSTER_CHARACTERS_SAMPLE,
    canCreate: true,
    switchLocked: false,
    locked: true,
    initialExpanded: false,
  },
};
