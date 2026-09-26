// The shared derived-shape helper for the scene overview family
// (webclient-scene-overview-component design D7; the showcase rule that a
// story is bound to the same reducer-derived shape the live wiring passes).
// Every SceneOverview / DockVerbPopover story builds its args here, by
// running the real `overviewMenu` / `verbMenuFor` of the exploration-menu
// model over a synthesized `exploration` panel. Every value is a fixed
// literal: no live server, LLM, or image data.
import ExplorationMenu from "../../lib/exploration_menu.js";

const DIRECTION_LABELS = ["北", "東", "南", "西", "東北", "西北", "東南", "西南", "上", "下"];

function exitRow(exit, index) {
  return {
    exit_ref: exit.ref || `exit-${index}`,
    label: exit.label,
    destination: exit.destination || null,
    enabled: exit.enabled !== false,
    disabled_reason: exit.reason ? { code: "blocked", message: exit.reason } : null,
  };
}

// A synthesized `exploration` panel (schema v3). `targets` are interact
// descriptors (`{identity, name, affordances}`), `entities` extra present
// characters with no interact descriptor, `objects` look-only things.
export function explorationPanelFixture({ exits = [], targets = [], entities = [], objects = [] } = {}) {
  return {
    schema_version: 3,
    available: true,
    kind: "exploration",
    move: exits.map(exitRow),
    look: {
      room: { identity: 900, display_name: "冒險者公會大廳", room: true },
      entities: [
        ...targets.map((target) => ({
          identity: target.identity,
          display_name: target.name,
          kind: target.kind || "npc",
          portrait_ref: null,
        })),
        ...entities.map((entity) => ({
          identity: entity.identity,
          display_name: entity.name,
          kind: "character",
          portrait_ref: null,
        })),
      ],
      objects: objects.map((object) => ({ identity: object.identity, display_name: object.name })),
    },
    interact: targets.map((target) => ({
      identity: target.identity,
      display_name: target.name,
      portrait_ref: null,
      affordances: target.affordances || [],
    })),
  };
}

// The destination names the exit chips read: the `nodes` of the committed
// local-map model (`destinationLabel` reads only `id` and `label`).
export function localMapFixture(nodes) {
  return { nodes: nodes.map(([id, label]) => ({ id, label })) };
}

// SceneOverview args: the overview menu exactly as the exploration root's
// resolver will return it.
export function overviewArgs(panel, { currentNode = "room:900", suggestions = null, localMap = null, focusedKey = null, active = true } = {}) {
  return {
    menu: ExplorationMenu.overviewMenu(panel, { currentNode, suggestions }),
    focusedKey,
    localMap,
    active,
  };
}

// DockVerbPopover args: the verb menu of one interact target.
export function verbArgs(panel, identity, { focusedKey = null } = {}) {
  const model = ExplorationMenu.buildMenus(panel, { currentNode: "room:900" });
  const target = ExplorationMenu.targetById(model, identity);
  return { menu: ExplorationMenu.verbMenuFor(model, target), focusedKey };
}

// Synthesized affordance rows.
export const AFFORDANCES = {
  talk: { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
  trade: { kind: "navigate", surface: "shop", label: "交易", enabled: true, disabled_reason: null },
  guild: { kind: "navigate", surface: "guild", label: "公會服務", enabled: true, disabled_reason: null },
  engage: { kind: "action", action_id: "explore.engage", label: "戰鬥", enabled: true, disabled_reason: null },
};

export { DIRECTION_LABELS };
