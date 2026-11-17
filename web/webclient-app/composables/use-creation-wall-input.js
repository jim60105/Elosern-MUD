// The preset card wall's keyboard owner (creation-preset-card-wall).
//
// One document capture listener, installed by the mounted wall and removed on
// unmount. It claims keys aimed at the wall itself, or at the persistent
// creation action dock while the dock stands on its preset-list frame (that
// frame carries no rows, so the wall is the only meaning those keys can
// have). A consumed key is stopped before the bubble-phase keyboard bridge,
// so no router row, raw command or text fallback ever receives it.
//
// - ← / →  move the local expansion one card, clamped at both ends.
// - 1–9    expand the card at that displayed ordinal; a missing ordinal is
//          consumed and inert.
// - Enter  on a native button inside the wall is left to the button (the
//          opening button expands, the primary button chooses), so the click
//          is the single activation; anywhere else in wall context it chooses
//          the expanded card.
// Repeated, modified and composing keys are never handled; a repeated Enter
// on a wall button is swallowed so a held key cannot re-activate it. Text
// entries and nested dialogs keep their own keys, and Escape, Tab, Space and
// the vertical arrows always reach their usual owners.
import { onBeforeUnmount, onMounted } from "vue";
import { isTextEntry } from "./use-window-hotkeys.js";

const DIGITS = new Set(["1", "2", "3", "4", "5", "6", "7", "8", "9"]);

function nestedSurface(root, target) {
  const surface = target.closest?.('[role="dialog"], [role="alertdialog"], dialog');
  return !!surface && surface !== root && root.contains(surface);
}

export function useCreationWallInput({ root, dockBrowsing, move, jump, choose }) {
  function consume(event) {
    event.preventDefault();
    event.stopPropagation();
  }

  function onCapture(event) {
    if (event.defaultPrevented) return;
    if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
    if (event.isComposing || event.keyCode === 229) return;
    const el = root.value;
    const target = event.target;
    // A wall that is not in the document (a detached render) owns no keys.
    if (!el || !el.isConnected || !target || target.nodeType !== 1) return;
    const inWall = el.contains(target);
    const inDock = !inWall && dockBrowsing() && !!target.closest?.("#action-dock");
    if (!inWall && !inDock) return;
    if (isTextEntry(target) || (inWall && nestedSurface(el, target))) return;
    const onButton = inWall && !!target.closest?.("button");
    if (event.repeat) {
      if (event.key === "Enter" && onButton) consume(event);
      return;
    }
    const key = event.key;
    if (key === "ArrowLeft" || key === "ArrowRight") {
      consume(event);
      move(key === "ArrowLeft" ? -1 : 1, inWall);
    } else if (DIGITS.has(key)) {
      consume(event);
      jump(Number(key) - 1, inWall);
    } else if (key === "Enter" && !onButton) {
      consume(event);
      choose();
    }
  }

  onMounted(() => document.addEventListener("keydown", onCapture, true));
  onBeforeUnmount(() => document.removeEventListener("keydown", onCapture, true));
}
