// Dock pane vocabulary (H3 webclient-hud-03-action-dock, tasks 4.4 + 5.1):
// a pure classifier that maps a committed frame to its pane kind, and the
// tab-bar badge counts derived from the committed payload only.
//
// No DOM access, no store access — the classifier is a pure function of the
// committed frame (the single navigation state, design D1).

// Classify a committed router frame into a pane kind (task 5.1). The items
// arrive normalized (the AppClient `dockItems` shape: `key`, `label`,
// `enabled`, `action_id`, `params`, `direction`, `destination`, `kind`,
// `scaleChoice`, `selected`). No DOM, no store access — a pure function of
// the committed frame.
//   - `outlet`:  move rows (exit list) — the draft's `.outlet` grid.
//   - `nav`:     look/interact target lists and keyword lists (`.ngrid`).
//   - `affordance`: a target-affordance frame (`.aff` buttons).
//   - `cards`:   the suggestions frame (`.sugs` cards).
//   - `skills`:  the combat skill frame (`.sk` rows beside the detail pane).
//   - `targets`: the combat target frame (`.tok` tokens).
//   - `scales`:  the 威力 scale step (`.scales`).
//   - `confirm`: a confirm/cancel confirmation frame (`.cast` / warning panel).
//   - `plain`:   anything else (root tab bar, empty frames).
export function classifyPane(frame) {
  const menu = (frame && frame.menu) || frame || {};
  const items = menu.items || [];
  if (items.length === 0) {
    return "plain";
  }
  // The standard `back` row (key === "back") is a navigation cell that closes
  // the frame; it must not break the `every(...)` pane checks. `rows` holds
  // the content rows (back excluded) for the `every` tests.
  const rows = items.filter((i) => i.key !== "back");

  // Confirmation frames: every content row is a `confirm-*` / `cancel-*` key.
  // (Block-body callback: the expression-body form trips a V8 parser quirk
  // when nested inside an `if (...every(...))` condition.)
  if (
    rows.length > 0 &&
    rows.every((i) => {
      return i.key && (i.key.startsWith("confirm-") || i.key.startsWith("cancel-"));
    })
  ) {
    return "confirm";
  }
  // Suggestions frame: the dismiss row, a generating/empty row, or an
  // `action-*` card key identifies it (the suggestion cards are keyed
  // `action-<code>` / `action-explore.talk_freeform`).
  if (
    items.some(
      (i) =>
        i.key === "action-options.dismiss" ||
        i.key === "suggestions-generating" ||
        i.key === "suggestions-empty" ||
        (i.key && i.key.startsWith("action-"))
    )
  ) {
    return "cards";
  }
  // The 威力 step: scale rows are marked `scaleChoice` or carry the
  // `choose-scale` action.
  if (items.some((i) => i.scaleChoice || i.action_id === "choose-scale")) {
    return "scales";
  }
  // The combat target frame: the AREA candidate rows carry the `toggle-target`
  // action or a client-local `selected` flag. The exploration interact target
  // rows (`target-<id>` + `openTarget`) are navigation rows, NOT this pane —
  // they are caught by the `nav` check below, so the `target-` key prefix alone
  // must not be used here.
  if (items.some((i) => i.action_id === "toggle-target" || i.selected === true)) {
    return "targets";
  }
  // The skill frame: rows carry the `open-skill` / `open-group` /
  // `open-category` actions.
  if (items.some((i) => i.action_id === "open-skill" || i.action_id === "open-group" || i.action_id === "open-category")) {
    return "skills";
  }
  // The move outlet: content rows keyed `exit-*` or carrying a `direction`.
  // (Block-body callback to dodge the V8 parser quirk on a grouped `&&`
  // containing a method call inside an `if (...every(...))`.)
  if (
    rows.length > 0 &&
    rows.every((i) => {
      return (i.key && i.key.startsWith("exit-")) || i.direction != null;
    })
  ) {
    return "outlet";
  }
  // Target-affordance frames: rows with the engage / party / freeform actions.
  if (items.some((i) =>
    i.action_id === "explore.engage" ||
    i.action_id === "explore.party_invite" ||
    i.action_id === "explore.talk_freeform"
  )) {
    return "affordance";
  }
  // Look / interact / wait / keyword navigation lists: the look rows carry the
  // `explore.look` action; the keyword rows are keyed `kw-*`; the exploration
  // interact target rows are navigation cells whose `surface` is a `target-<id>`
  // key (they open the target-affordance frame).
  if (
    (rows.length > 0 && rows.every((i) => i.action_id === "explore.look")) ||
    items.some((i) => {
      return i.key && i.key.startsWith("kw-");
    }) ||
    items.some((i) => i.navigation && i.surface && i.surface.startsWith("target-"))
  ) {
    return "nav";
  }
  return "plain";
}

// Tab-bar badges (task 4.4): derived from the committed payload only —
// `互動` = `exploration.interact.length`, `建議` = `suggestions.cards.length`,
// `技能` = the flattened skill-descriptor count. No badge for an
// unknowable or zero count.
export function badgeCount(surface, view) {
  const panels = (view && view.panels) || {};
  switch (surface) {
    case "interact": {
      const panel = panels.exploration || {};
      return Array.isArray(panel.interact) ? panel.interact.length : 0;
    }
    case "suggestions": {
      const sugg = view && view.suggestions;
      return sugg && Array.isArray(sugg.cards) ? sugg.cards.length : 0;
    }
    case "skills": {
      const panel = panels.context_actions || {};
      if (panel.kind !== "combat") {
        return 0;
      }
      let count = 0;
      ((panel.skills || [])).forEach((category) => {
        ((category.groups || [])).forEach((group) => {
          count += (group.skills || []).length;
        });
      });
      return count;
    }
    default:
      return 0;
  }
}

// The badge shows only for a positive count (no badge for zero/unknowable).
export function badgeVisible(count) {
  return typeof count === "number" && count > 0;
}
