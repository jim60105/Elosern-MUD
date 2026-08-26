import { h } from "vue";
import HudDrawer from "../../components/HudDrawer.vue";
import CharacterStatusDrawer from "../../components/CharacterStatusDrawer.vue";
import {
  STATUS_PANEL_SAMPLE,
  STATUS_PANEL_COMBAT_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
  CHARACTER_PANEL_UNDISGUISED_SAMPLE,
} from "../fixtures.js";

// CharacterStatusDrawer (H4, task 5.7): the 角色狀態 drawer body, shown
// inside the shared right-anchored HudDrawer chrome. Deterministic and
// offline. The combat story keeps the status vitals + conditions visible
// while the character sections are unavailable (registry-owned reason).

// The component story title must be the first title key in the file, because
// the component-coverage gate keys off the first match. Placing the default
// export before the render helper guarantees the gate sees the manifest name.
export default {
  title: "Data/CharacterStatusDrawer",
  component: CharacterStatusDrawer,
};

function renderDrawer(args) {
  // A character panel in its registry-owned unavailable form (no fabricated
  // rows) for the combat story.
  const character =
    args.combat
      ? { schema_version: 3, available: false, kind: "character", reason: { code: "no_puppet", message: "你已離開角色" } }
      : args.undisguised
        ? CHARACTER_PANEL_UNDISGUISED_SAMPLE
        : CHARACTER_PANEL_SAMPLE;
  return {
    render: () =>
      h(
        "div",
        { style: "position: relative; width: 100%; height: 520px; background: var(--ink-950); overflow: hidden;" },
        [
          h(
            HudDrawer,
            { open: true, title: "角色狀態", subtitle: "status", drawerKey: "status", onClose: () => {} },
            {
              default: () =>
                h(CharacterStatusDrawer, {
                  status: args.combat ? STATUS_PANEL_COMBAT_SAMPLE : STATUS_PANEL_SAMPLE,
                  character,
                  lowHp: false,
                  onOpenSkill: () => {},
                }),
            },
          ),
        ],
      ),
  };
}

export const Full = {
  render: renderDrawer,
  args: {},
};

export const Undisguised = {
  render: renderDrawer,
  args: { undisguised: true },
};

export const Combat = {
  render: renderDrawer,
  args: { combat: true },
};
