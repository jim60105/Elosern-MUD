// The window hotkeys (webclient-main-navigation-hotkeys; design §8 of the
// party member management design): P 隊伍 (the party window on its last
// tab), B 背包, C 狀態, K 技能, L 系譜, J 任務 and M 地圖. Each key runs the very
// opener its navigation control (or the party window tab alias) runs, so the
// surface captures the focused element as its opener exactly as a click
// does.
//
// One document `keydown` listener in the bubble phase, beside the keyboard
// bridge (which never claims a letter). A key acts only when:
// - nothing consumed it already, it is not a repeat, and no modifier is held
//   (Shift included, so a typed capital never opens a window);
// - no IME composition is in progress;
// - focus is outside every text input, textarea, select and contenteditable
//   element;
// - no modal question stands (the cross-side or party-exit QuestionCard, a
//   rendered alertdialog or aria-modal surface) and the mode is not creation;
// - no drawer, overlay or full log is open — focus-trapped surfaces own their
//   keys. The one exception: while the party window itself is open, its tab
//   keys (P B C K L) switch it live;
// - the surface is available: an absent 隊伍 (no committed party panel), an
//   absent or disabled 任務 and the 地圖 entry in combat ignore their keys.
import { onBeforeUnmount, onMounted } from "vue";

// The party window's tab aliases, as `openHudDrawer` resolves them; P is the
// bare window, which reopens on the remembered tab.
const PARTY_KEYS = { KeyP: "party", KeyB: "inventory", KeyC: "status", KeyK: "skill", KeyL: "lineage" };
const LETTER_CODES = { p: "KeyP", b: "KeyB", c: "KeyC", k: "KeyK", l: "KeyL", j: "KeyJ", m: "KeyM" };

// `event.code` names the physical key whatever the layout (a Zhuyin or
// Cyrillic layout still reports KeyP); `event.key` is the fallback for
// synthetic events that carry no code.
export function hotkeyCode(event) {
  if (typeof event.code === "string" && /^Key[A-Z]$/.test(event.code)) return event.code;
  const key = typeof event.key === "string" ? event.key.toLowerCase() : "";
  return LETTER_CODES[key] ?? null;
}

export function isTextEntry(el) {
  if (!el || el.nodeType !== 1) return false;
  if (el.isContentEditable) return true;
  const tag = el.tagName;
  if (tag === "TEXTAREA" || tag === "SELECT") return true;
  if (tag === "INPUT") {
    const type = (el.getAttribute("type") || "text").toLowerCase();
    return !["button", "checkbox", "radio", "range", "reset", "submit", "image", "color", "file"].includes(type);
  }
  const editable = el.closest && el.closest('[contenteditable]:not([contenteditable="false"])');
  return !!editable;
}

// A surface that is actually on screen: connected, not hidden by an
// ancestor, and not `display: none`.
function rendered(el) {
  if (!el.isConnected || el.closest('[hidden], [inert], [aria-hidden="true"]')) return false;
  const style = window.getComputedStyle(el);
  return style.display !== "none" && style.visibility !== "hidden";
}

// A modal question on screen: the store's held questions, or any rendered
// alertdialog or aria-modal surface other than a drawer's own frame (the
// open drawer is judged by `view.hudDrawer`, so the party window's frame does
// not count, while a confirmation drawn inside it does).
function modalOpen(view) {
  if (view.crossSideConfirm || view.partyExitConfirm) return true;
  return [...document.querySelectorAll('[role="alertdialog"], [aria-modal="true"]:not([data-testid="hud-drawer"])')].some(rendered);
}

export function useWindowHotkeys(store, { openParty, openQuests, openMap, questsEnabled, fullLogOpen }) {
  function onKeydown(event) {
    if (event.defaultPrevented || event.repeat) return;
    if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) return;
    if (event.isComposing || event.keyCode === 229) return;
    const code = hotkeyCode(event);
    if (!code || !(code in PARTY_KEYS || code === "KeyJ" || code === "KeyM")) return;
    if (isTextEntry(event.target) || isTextEntry(document.activeElement)) return;
    const view = store.view;
    if (!view || view.mode === "creation" || !view.mode) return;
    if (modalOpen(view)) return;
    if (view.hudOverlay || fullLogOpen()) return;
    const partyOpen = view.hudDrawer === "party";
    if (view.hudDrawer && !(partyOpen && code in PARTY_KEYS)) return;

    let acted = false;
    if (code in PARTY_KEYS) {
      if (!store.partyAvailable) return;
      acted = openParty(PARTY_KEYS[code]) !== false;
    } else if (code === "KeyJ") {
      if (view.mode === "combat" || !questsEnabled()) return;
      openQuests();
      acted = true;
    } else if (code === "KeyM") {
      if (view.mode === "combat") return;
      openMap();
      acted = true;
    }
    if (acted) event.preventDefault();
  }

  onMounted(() => document.addEventListener("keydown", onKeydown));
  onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));
  return { onWindowHotkey: onKeydown };
}
