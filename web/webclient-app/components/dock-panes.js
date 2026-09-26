// Dock pane vocabulary (H3 webclient-hud-03-action-dock, tasks 4.4 + 5.1):
// a pure classifier that maps a committed frame to its pane kind, and the
// tab-bar badge counts derived from the committed payload only.
//
// No DOM access, no store access — the classifier is a pure function of the
// committed frame (the single navigation state, design D1).

// Classify a committed router frame into a pane kind (task 5.1). The items
// arrive normalized (the AppClient `dockItems` shape: `key`, `label`,
// `enabled`, `action_id`, `params`, `kind`, `scaleChoice`, `selected`). No
// DOM, no store access — a pure function of the committed frame.
//   - `cards`:   the suggestions frame (`.sugs` cards).
//   - `skills`:  the combat skill frame (`.sk` rows beside the detail pane).
//   - `targets`: the combat target frame (`.tok` tokens).
//   - `scales`:  the 威力 scale step (`.scales`).
//   - `confirm`: a confirm/cancel confirmation frame (`.cast` / warning panel).
//   - `plain`:   anything else (root tab bar, empty frames).
//
// The retired move frame's `outlet` kind is gone with the frame
// (webclient-retire-exploration-submenus): exits are the scene overview's
// chips, which that component renders itself.
// The retired `nav` kind went with the scripted-keyword frame, and the
// `affordance` kind with the exploration target frame, which the verb popover
// replaced (webclient-talk-open-dock): a frame that once classified as either
// now falls through to `plain`, which renders the same rows through the shared
// row renderer.
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
  // rows are not a DockMenu frame at all any more (the verb popover replaced
  // them), so the `target-` key prefix alone must not be used here.
  if (items.some((i) => i.action_id === "toggle-target" || i.selected === true)) {
    return "targets";
  }
  // The skill frame: rows carry the `open-skill` / `open-group` /
  // `open-category` actions.
  if (items.some((i) => i.action_id === "open-skill" || i.action_id === "open-group" || i.action_id === "open-category")) {
    return "skills";
  }
  return "plain";
}

// Tab-bar badges (task 4.4): derived from the committed payload only —
// `技能` = the flattened skill-descriptor count. The combat root is the only
// frame that renders as a tab bar (webclient-scene-overview-swap), so its
// `skills` tab is the only badged surface. No badge for an unknowable or
// zero count.
export function badgeCount(surface, view) {
  const panels = (view && view.panels) || {};
  switch (surface) {
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
