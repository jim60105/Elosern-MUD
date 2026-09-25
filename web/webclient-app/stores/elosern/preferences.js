// The presentation-preferences group of the composed Elosern store.
//
// H5 (webclient-hud-05-overlays-and-command-line, tasks 7.5/7.8): the
// presentation-preferences slice. Client-local presentation state
// (webclient-component-showcase delta): the narrative prose scale
// (`fontScale`), the text-to-HTML narrative toggle (`text2html`), the
// optional reduced-motion override (`reducedMotion` — `null` means no
// override, the OS `prefers-reduced-motion` applies) and the colorblind
// status palette (`colorblind`). C7 (webclient-typewriter-reading-prefs,
// design D10) adds the reading preferences the message window reads as
// props: the typing speed (`textSpeed`, one of `TEXT_SPEEDS`) and the
// opt-in auto-advance (`autoAdvance`). No settings control dispatches a
// `ui_action`; each preference is applied to the document's presentation
// tokens immediately, is persisted through the versioned,
// presentation-only layout store, and is re-applied at load. The store's
// own LayoutStore instance is the only writer (main.js's instance stays
// load-only): a preference save reloads the latest validated wrapper
// before writing, so the caller's `dimensions` and `tabs` are preserved.

import LayoutStore from "../../lib/layout_store.js";
import { TEXT_SPEEDS } from "../../lib/message_reveal.js";

export function applyPreferences(ctx) {
  const layoutPersistence = LayoutStore.createStore({ storage: window.localStorage });
  const prefs = {
    fontScale: 1,
    text2html: true,
    // Optional key: absent in the stored wrapper = no override (task 7.5).
    reducedMotion: null,
    colorblind: false,
    textSpeed: "normal",
    autoAdvance: false,
  };
  ctx.prefs = prefs;

  function applyPresentationPreferences() {
    const root = document.documentElement;
    // The three prose-scale targets (design D13): the message window's page
    // text, the full-log surface's lines and the prompt line read this
    // token; no HUD/dock/drawer/overlay chrome reads it.
    root.style.setProperty("--prose-scale", String(prefs.fontScale));
    if (prefs.reducedMotion) {
      root.setAttribute("data-reduced-motion", prefs.reducedMotion);
    } else {
      root.removeAttribute("data-reduced-motion");
    }
    if (prefs.colorblind) {
      root.setAttribute("data-colorblind", "on");
    } else {
      root.removeAttribute("data-colorblind");
    }
    ctx.publishView();
  }

  function persistPresentationPreferences() {
    // Reload the latest validated wrapper before writing (task 7.8): an
    // unknown or earlier stored version resets to the default with every
    // preference re-applied rather than half-applied.
    const current = layoutPersistence.load();
    const wrapper = current.state;
    wrapper.preferences = {
      text2html: prefs.text2html,
      fontScale: prefs.fontScale,
      colorblind: prefs.colorblind,
      textSpeed: prefs.textSpeed,
      autoAdvance: prefs.autoAdvance,
    };
    // The reducedMotion key is optional (task 7.5): only write it when the
    // override is explicit. The layout store validates it as a boolean —
    // `true` forces reduced motion ("on"), `false` forces full motion
    // ("off"); absence in the stored wrapper means "no override" (the OS
    // `prefers-reduced-motion` applies).
    if (prefs.reducedMotion) {
      wrapper.preferences.reducedMotion = prefs.reducedMotion === "on";
    }
    layoutPersistence.save(wrapper);
  }

  // H5 (tasks 7.5/7.8): re-apply the persisted presentation preferences at
  // load (the facade calls this at the original site — after the signature
  // variables `publishView` touches, so the init-time `publishView` cannot
  // hit a temporal-dead-zone).
  ctx.loadPresentationPreferences = function loadPresentationPreferences() {
    const result = layoutPersistence.load();
    const stored = (result.state && result.state.preferences) || {};
    if (typeof stored.fontScale === "number" && isFinite(stored.fontScale)) {
      prefs.fontScale = Math.min(2, Math.max(0.5, stored.fontScale));
    }
    if (typeof stored.text2html === "boolean") {
      prefs.text2html = stored.text2html;
    }
    // The `reducedMotion` key is optional (task 7.5): stored as a boolean
    // override — `true` forces reduced motion ("on"), `false` forces full
    // motion ("off"); its absence means "no override" (the OS
    // `prefers-reduced-motion` applies).
    if (typeof stored.reducedMotion === "boolean") {
      prefs.reducedMotion = stored.reducedMotion ? "on" : "off";
    }
    if (typeof stored.colorblind === "boolean") {
      prefs.colorblind = stored.colorblind;
    }
    if (TEXT_SPEEDS.includes(stored.textSpeed)) {
      prefs.textSpeed = stored.textSpeed;
    }
    if (typeof stored.autoAdvance === "boolean") {
      prefs.autoAdvance = stored.autoAdvance;
    }
    applyPresentationPreferences();
  };

  ctx.setFontScale = function setFontScale(value) {
    if (typeof value !== "number" || !isFinite(value)) {
      return;
    }
    prefs.fontScale = Math.min(2, Math.max(0.5, value));
    applyPresentationPreferences();
    persistPresentationPreferences();
  };

  ctx.setTextToHtml = function setTextToHtml(on) {
    prefs.text2html = !!on;
    applyPresentationPreferences();
    persistPresentationPreferences();
  };

  ctx.setReducedMotion = function setReducedMotion(value) {
    // `null` = no override (the OS preference applies); `"on"` forces
    // reduced motion; `"off"` beats the OS `prefers-reduced-motion` media
    // query (task 7.6).
    if (value !== null && value !== "on" && value !== "off") {
      return;
    }
    prefs.reducedMotion = value;
    applyPresentationPreferences();
    persistPresentationPreferences();
  };

  ctx.setColorblind = function setColorblind(on) {
    prefs.colorblind = !!on;
    applyPresentationPreferences();
    persistPresentationPreferences();
  };

  // C7 (design D10): the reading preferences are read by the message window
  // as props, so they write no document attribute; applying them publishes
  // the view.
  ctx.setTextSpeed = function setTextSpeed(value) {
    if (!TEXT_SPEEDS.includes(value)) {
      return;
    }
    prefs.textSpeed = value;
    applyPresentationPreferences();
    persistPresentationPreferences();
  };

  ctx.setAutoAdvance = function setAutoAdvance(on) {
    prefs.autoAdvance = !!on;
    applyPresentationPreferences();
    persistPresentationPreferences();
  };
}
