// Action-dock item contract (B2, webclient-vue-03-showcase-action): derives
// the preserved `action-`/`target-` item keys from `context_actions` v5 panel
// items and maps an activated item to the exact OOB action intent (the
// `action_id` + `payload` of the `ui_action` envelope). Pure functions — no
// DOM, no store (C1) — so the key/intent contract stays Node-testable and the
// C3/C4 browser contract can rely on component-owned keys (design D1/D5,
// Phase-0 audit §2.3: `data-item-key` row identity, `target-` prefix in
// target menus).
//
// Item shapes (all fields come from the validated `context_actions` panel —
// nothing is invented here):
// - action affordance: { action_id, label, params, freeform, navigation,
//   enabled, disabled_reason } — its `params` is the dispatcher-normalized
//   action payload, so the intent is exactly { action_id, params }.
// - navigation affordance: { surface, label, navigation, enabled,
//   disabled_reason } — opens a local surface (guild/shop), not an OOB action.
// - target entry: { identity, label, enabled, disabled_reason } — a target
//   selection frame; `target-<identity>` mirrors the legacy literal key.

const ACTION_PREFIX = "action-";
const TARGET_PREFIX = "target-";

function classify(item) {
  if (item && item.navigation === true && typeof item.surface === "string") {
    return "navigation";
  }
  if (item && typeof item.identity === "string") {
    return "target";
  }
  if (item && typeof item.action_id === "string") {
    return "action";
  }
  throw new TypeError("dock item must be an action, navigation, or target entry");
}

// Derive one preserved item key per item, aligned with the input order.
// Duplicates get a positional suffix (`-2`, `-3`, ...) so a bounded frame can
// never produce two cells with the same dispatch handle.
export function dockItemKeys(items) {
  const seen = new Map();
  return items.map((item) => {
    const kind = classify(item);
    const base =
      kind === "target"
        ? TARGET_PREFIX + item.identity
        : ACTION_PREFIX + (kind === "navigation" ? item.surface : item.action_id);
    const count = (seen.get(base) ?? 0) + 1;
    seen.set(base, count);
    return count === 1 ? base : `${base}-${count}`;
  });
}

// The exact OOB action intent for an activated item: the `action_id` +
// `payload` fields the `ui_action` envelope would carry. `null` for local
// (navigation/target) cells — they never invent an OOB action.
export function actionIntentForItem(item) {
  const kind = classify(item);
  if (kind !== "action") {
    return null;
  }
  return {
    action_id: item.action_id,
    payload: item.params === undefined ? {} : { ...item.params },
  };
}

// The disabled text for a cell: the server-authored reason message when the
// server carries one, otherwise `null` (the cell still gets the preserved
// `（無法使用）` suffix, which the component renders from `enabled` alone).
export function disabledReasonText(item) {
  if (item && item.enabled !== false) {
    return null;
  }
  const reason = item ? item.disabled_reason : null;
  return reason && typeof reason.message === "string" ? reason.message : null;
}
