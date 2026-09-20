// The client-local toast queue group of the composed Elosern store
// (webclient-action-feedback D1).

import { ref, onScopeDispose } from "vue";
import { TOAST_LIFETIME_MS, TOAST_QUEUE_MAX } from "./constants.js";

// The frozen tone vocabulary (webclient-action-feedback): an unknown tone is
// rejected, not coerced (the openHudDrawer precedent).
const TOAST_TONES = new Set(["info", "crit"]);

export function applyToasts(ctx) {
  // Declared above the initial view because `initialView()` calls `buildView`,
  // which reads it (TDZ). The array is the ONE mutable reactive proxy:
  // `buildView` exposes the same reference on every publish, so pushes and
  // dismisses re-render consumers without a republish — and
  // `handleActionResult` pushes DURING a publish, where a nested republish
  // would recurse.
  const toasts = ref([]); // [{id, title, sub?, tone}]
  ctx.toasts = toasts;
  // Per-entry auto-dismiss timers (internal bookkeeping; never reaches the
  // entry shape or the view).
  const toastTimers = new Map();
  let toastIdCounter = 0;

  // Push one toast, returning its id; a malformed entry is rejected, not
  // coerced. A full queue evicts the oldest entries first (FIFO). Every
  // pushed toast self-dismisses after TOAST_LIFETIME_MS unless clicked away
  // earlier.
  ctx.pushToast = function pushToast(entry) {
    const item = entry || {};
    if (typeof item.title !== "string" || item.title.trim() === "") {
      console.warn("pushToast: missing or blank title rejected (not coerced)");
      return null;
    }
    if (!TOAST_TONES.has(item.tone)) {
      console.warn(`pushToast: unknown tone "${item.tone}" rejected (not coerced)`);
      return null;
    }
    const toast = { id: ++toastIdCounter, title: item.title, tone: item.tone };
    if (typeof item.sub === "string" && item.sub.trim() !== "") {
      toast.sub = item.sub;
    }
    toasts.value.push(toast);
    while (toasts.value.length > TOAST_QUEUE_MAX) {
      dismissToast(toasts.value[0].id);
    }
    toastTimers.set(toast.id, setTimeout(() => dismissToast(toast.id), TOAST_LIFETIME_MS));
    return toast.id;
  };

  // Remove one toast by id (also cancels its pending timer). Returns whether
  // an entry was removed; an unknown id is a no-op.
  function dismissToast(id) {
    const timer = toastTimers.get(id);
    if (timer !== undefined) {
      clearTimeout(timer);
      toastTimers.delete(id);
    }
    const index = toasts.value.findIndex((toast) => toast.id === id);
    if (index === -1) {
      return false;
    }
    toasts.value.splice(index, 1);
    return true;
  }
  ctx.dismissToast = dismissToast;

  // Scope-dispose teardown: a disposed store must leave no timer that can
  // fire into it later. The queue is client-local, so its entries die with
  // the store instance alongside their timers (transport resets, by
  // contrast, deliberately KEEP the queue — toasts survive a reconnect).
  onScopeDispose(() => {
    for (const timer of toastTimers.values()) {
      clearTimeout(timer);
    }
    toastTimers.clear();
    toasts.value.length = 0;
  });
}
