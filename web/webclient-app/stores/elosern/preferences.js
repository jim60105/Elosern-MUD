// The presentation-preferences group of the composed Elosern store.
//
// H5 (webclient-hud-05-overlays-and-command-line, tasks 7.5/7.8): the
// presentation-preferences slice. Client-local presentation state
// (webclient-component-showcase delta): the narrative prose scale
// (`fontScale`), the text-to-HTML narrative toggle (`text2html`), the
// optional motion level (`motionLevel` — `null` means nothing stored, so the
// OS `prefers-reduced-motion` preference is followed live) and the colorblind
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
//
// C11a (webclient-motion-level, design D1/D2): the store is the only
// motion-level resolver. It holds `prefs.motionLevel` (`null` or one of
// `MOTION_LEVELS`) and one `matchMedia` query; `ctx.effectiveMotionLevel()`
// resolves the stored level against the live OS preference, and
// `applyPresentationPreferences` writes the EFFECTIVE level to
// `<html data-motion>` — the single value the stylesheet's token blocks and
// the script both read. `data-reduced-motion` is gone.

import LayoutStore from "../../lib/layout_store.js";
import { MOTION_LEVELS, resolveMotionLevel } from "../../lib/motion_level.js";
import { TEXT_SPEEDS } from "../../lib/message_reveal.js";

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

export function applyPreferences(ctx) {
  const layoutPersistence = LayoutStore.createStore({ storage: window.localStorage });
  const prefs = {
    fontScale: 1,
    text2html: true,
    // Optional key: absent in the stored wrapper = nothing stored, so the OS
    // preference is followed (design D2).
    motionLevel: null,
    colorblind: false,
    textSpeed: "normal",
    autoAdvance: false,
  };
  ctx.prefs = prefs;

  // One query for the page (design D1): the store lives as long as the
  // document, so the listener is never removed.
  const query =
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia(REDUCED_MOTION_QUERY)
      : null;

  // The one resolved value (design D1): the stored level when it is valid,
  // else the live OS preference.
  ctx.effectiveMotionLevel = function effectiveMotionLevel() {
    return resolveMotionLevel(prefs.motionLevel, !!(query && query.matches));
  };

  function applyPresentationPreferences() {
    const root = document.documentElement;
    // The three prose-scale targets (design D13): the message window's page
    // text, the full-log surface's lines and the prompt line read this
    // token; no HUD/dock/drawer/overlay chrome reads it.
    root.style.setProperty("--prose-scale", String(prefs.fontScale));
    // The effective level, always written (design D1): the stylesheet's
    // `:root[data-motion="…"]` blocks own every motion token from the first
    // apply on, so the `:root:not([data-motion])` OS fallback only covers the
    // frames before this runs (and Storybook, where no store runs).
    root.setAttribute("data-motion", ctx.effectiveMotionLevel());
    if (prefs.colorblind) {
      root.setAttribute("data-colorblind", "on");
    } else {
      root.removeAttribute("data-colorblind");
    }
    ctx.publishView();
  }

  // A live OS change re-applies the presentation while nothing is stored
  // (design D1). It persists nothing: the effective level is derived, and a
  // store reset must return to "follow the OS".
  if (query && typeof query.addEventListener === "function") {
    query.addEventListener("change", () => {
      if (prefs.motionLevel === null) {
        applyPresentationPreferences();
      }
    });
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
    // The motionLevel key is optional (design D2): only write it when a level
    // is stored. Its absence means "follow the OS".
    if (prefs.motionLevel !== null) {
      wrapper.preferences.motionLevel = prefs.motionLevel;
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
    // The `motionLevel` key is optional (design D2): a stored value outside
    // the three levels is discarded, as if nothing were stored, so the OS
    // preference applies again.
    if (MOTION_LEVELS.includes(stored.motionLevel)) {
      prefs.motionLevel = stored.motionLevel;
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

  ctx.setMotionLevel = function setMotionLevel(level) {
    // Only the three levels may be stored (design D1). A stored level always
    // overrides the OS preference; there is no "follow the system" value —
    // the unset state exists only until the first choice, or after a store
    // reset.
    if (!MOTION_LEVELS.includes(level)) {
      return;
    }
    prefs.motionLevel = level;
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
