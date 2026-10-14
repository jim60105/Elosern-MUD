// The shared derived-shape helper for the scene overview family
// (webclient-scene-overview-component design D7; the showcase rule that a
// story is bound to the same reducer-derived shape the live wiring passes).
// Every PresenceRail, ExitCompass, and ChoiceCard story builds its args
// here, by running the real `presenceEntries` /
// `verbMenuFor` / `waitItems` / `suggestionsMenu` of the exploration-menu
// model over a synthesized `exploration` panel. Every value is a fixed
// literal: no live server, LLM, or image data.
import ExplorationMenu from "../../lib/exploration_menu.js";
import { resolveTargets } from "../../components/compass-model.js";
import { localMapModelFor } from "./local_map.js";
import { overflowCardRows, verbCardRows } from "../../composables/use-person-focus.js";
import { suggestionsCardContent, waitCardRows } from "../../composables/use-room-actions.js";

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

// A synthesized available `exploration` panel at the current schema version
// (v4). `targets` are interact descriptors (`{identity, name, affordances}`),
// `entities` extra present characters with no interact descriptor, `objects`
// look-only things, and `portraits` maps an identity to the wire-valid
// decimal `portrait_ref` the presenter would supply (null everywhere else).
// The values are hand-authored fixtures, NOT producer evidence: only the
// server packet can establish that a reference names a catalog image.
export function explorationPanelFixture({
  exits = [],
  targets = [],
  entities = [],
  objects = [],
  portraits = {},
} = {}) {
  const refFor = (identity) => (Object.hasOwn(portraits, identity) ? portraits[identity] : null);
  return {
    schema_version: 4,
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
          portrait_ref: refFor(target.identity),
        })),
        ...entities.map((entity) => ({
          identity: entity.identity,
          display_name: entity.name,
          kind: "character",
          portrait_ref: refFor(entity.identity),
        })),
      ],
      objects: objects.map((object) => ({ identity: object.identity, display_name: object.name })),
    },
    interact: targets.map((target) => ({
      identity: target.identity,
      display_name: target.name,
      portrait_ref: refFor(target.identity),
      affordances: target.affordances || [],
    })),
  };
}

// A minimal local-map model carrying only destination names (`id` and
// `label`, all `destinationLabel` reads), for the dialogue exits list.
export function localMapFixture(nodes) {
  return { nodes: nodes.map(([id, label]) => ({ id, label })) };
}

// PresenceRail args (exploration-presence-rail): the rail entries exactly as
// the store publishes them — the panel's own `portrait_ref` values flow
// through `presenceEntries` untouched, so a story supplies a face crop by
// threading the reference into the fixture's `portraits` map.
export function presenceArgs(panel, { artPanel = null, motionLevel = "full" } = {}) {
  return { entries: ExplorationMenu.presenceEntries(panel), artPanel, motionLevel };
}

// ChoiceCard args for one interact target's verb card: `verbMenuFor`'s rows
// mapped exactly as the person-focus wiring maps them.
export function verbCardArgs(panel, identity) {
  const model = ExplorationMenu.buildMenus(panel, { currentNode: "room:900" });
  const target = ExplorationMenu.targetById(model, identity);
  const rows = verbCardRows(ExplorationMenu.verbMenuFor(model, target).items);
  return { rows, trailingIndex: rows.length - 1, ariaLabel: `${target.display_name}：選擇行動` };
}

// ChoiceCard args for the presence overflow card.
export function overflowCardArgs(panel) {
  const rows = overflowCardRows(ExplorationMenu.presenceEntries(panel));
  return { rows, trailingIndex: rows.length - 1, caption: "在場", ariaLabel: "其餘在場者與物件" };
}

// ChoiceCard args for the wait card and the suggestions card
// (exploration-room-actions): the builders' rows mapped exactly as the room
// actions' wiring maps them.
export function waitCardArgs({ locked = false } = {}) {
  const rows = waitCardRows(ExplorationMenu.waitItems().filter((item) => !item.goBack), locked);
  return { rows, trailingIndex: rows.length - 1, caption: "等待", ariaLabel: "等待與休息", testId: "wait-card" };
}

export function suggestionsCardArgs(suggestions) {
  const items = ExplorationMenu.suggestionsMenu(suggestions).items.filter((item) => !item.goBack);
  const content = suggestionsCardContent({ status: suggestions.status, items });
  return {
    rows: content.rows,
    notes: content.notes,
    trailingIndex: content.trailingIndex,
    caption: "建議",
    ariaLabel: "建議",
    testId: "suggestions-card",
  };
}

// ExitCompass args (exploration-exit-compass): the compass targets exactly as
// the pane derives them — the exploration resolver's exit rows
// (`ExplorationMenu.exitTargets`) resolved against the store-shaped
// `localMapModel` of a committed `local_map` panel. `localMap` null means no
// local map is committed (the rows then carry no current node).
export function compassArgs(panel, localMap, { arrivalKey = 1, busy = false, motionLevel = "full" } = {}) {
  const currentNode = localMap ? localMap.current_node : null;
  const model = localMap ? localMapModelFor(localMap) : null;
  const rows = ExplorationMenu.exitTargets(panel, { currentNode });
  return {
    targets: resolveTargets(rows, model, { currentNode }),
    arrivalKey,
    busy,
    active: true,
    motionLevel,
    localMapModel: model,
  };
}

// Synthesized affordance rows.
export const AFFORDANCES = {
  talk: { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
  trade: { kind: "navigate", surface: "shop", label: "交易", enabled: true, disabled_reason: null },
  guild: { kind: "navigate", surface: "guild", label: "公會服務", enabled: true, disabled_reason: null },
  engage: { kind: "action", action_id: "explore.engage", label: "戰鬥", enabled: true, disabled_reason: null },
};

export { DIRECTION_LABELS };
