// The effective reduced-motion flag (OpenSpec change
// webclient-typewriter-reading-prefs, design D4). The stored override wins:
// `"on"` is reduced, `"off"` is full motion. With no override (`null`) the
// flag follows the operating system's `prefers-reduced-motion: reduce`
// live, through a `change` listener removed on unmount. Without
// `matchMedia` (jsdom with no mock) the flag is false. This mirrors the
// motion-token rule in `styles/tokens.css`, so the stylesheet and the
// typewriter never disagree.
//
// C11 (webclient-motion-level) replaces this composable, and the override,
// with the three-level `motionLevel`.
import { computed, onBeforeUnmount, ref } from "vue";

const QUERY = "(prefers-reduced-motion: reduce)";

export function useReducedMotion(override) {
  const osReduced = ref(false);
  let media = null;

  function onChange(event) {
    osReduced.value = !!(event && event.matches);
  }

  if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
    media = window.matchMedia(QUERY);
    osReduced.value = !!(media && media.matches);
    if (media && typeof media.addEventListener === "function") {
      media.addEventListener("change", onChange);
    }
  }

  onBeforeUnmount(() => {
    if (media && typeof media.removeEventListener === "function") {
      media.removeEventListener("change", onChange);
    }
    media = null;
  });

  return computed(() => {
    const value = typeof override === "function" ? override() : override;
    if (value === "on") {
      return true;
    }
    if (value === "off") {
      return false;
    }
    return osReduced.value;
  });
}
