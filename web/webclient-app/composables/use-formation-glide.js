// The shared-scale glide (OpenSpec change webclient-combat-formation, design
// D3): every figure on both sides is the same height in every frame of a
// mode crossing and of a roster change.
//
// Persisting figures inside combat glide on their slots' own CSS transition
// (left/top/width/height, one rule for both line-ups). What CSS alone cannot
// do is handled here, on each figure's inner `.formation-figure` wrapper
// (`data-glide-key`), with one FLIP for every figure in the same frame:
// - a mode crossing (no formation <-> a formation): the exploration layout is
//   CSS-driven (right/bottom, a shifted row), so it cannot be a transition
//   endpoint; each party figure is inverted from the box it showed before the
//   commit to its new box (translate + uniform scale about its bottom-left),
//   then released over the actor duration times the travel factor;
// - a figure that appears (every foe on the entry, a foe that joins): it is
//   inverted to the height the persisting figures showed before the commit,
//   about its bottom centre, and released with them.
// The "first" boxes are read in a pre-flush watcher of the client root, which
// runs before any component of that render patches the DOM (the stage's mode
// and formation attributes included); the "last" boxes in a post-flush
// watcher. Leaving figures are left alone: they fade where they stand.
// Below `full`, on a reconnect and on a resize nothing is inverted, and any
// glide still in flight is cleared, so the figures stand at their final boxes.
import { watch } from "vue";

export const GLIDE_TRANSITION = "transform calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard)";
// The longest a glide may hold its inline styles if no transition event comes.
const CLEANUP_MS = 2000;
const LEAVING = ".foe-leave-active, .foes-enter-leave-active";

// The inverse transform that shows a figure laid out at `last` where `first`
// was: about the bottom-left corner when the figure moved (`first` known), or
// a pure scale about the bottom centre to `height` when it appears. Pure.
export function invertBox(last, first, height) {
  if (!last || !(last.height > 0)) return null;
  if (first && first.height > 0) {
    const dx = first.left - last.left;
    const dy = first.top + first.height - (last.top + last.height);
    const scale = first.height / last.height;
    return { origin: "0 100%", transform: `translate(${dx}px, ${dy}px) scale(${scale})` };
  }
  if (height > 0) {
    return { origin: "50% 100%", transform: `scale(${height / last.height})` };
  }
  return null;
}

function rectOf(el) {
  const r = el.getBoundingClientRect();
  return { left: r.left, top: r.top, width: r.width, height: r.height };
}

function clearGlide(el) {
  el.__formationGlide = null;
  el.style.transition = "";
  el.style.transform = "";
  el.style.transformOrigin = "";
}

// `rootRef`: the client root; `formation`: the computed formation (or null);
// `enabled`: a getter, true when a change may glide.
export function useFormationGlide({ rootRef, formation, enabled }) {
  let first = null;

  const figures = () => [...(rootRef.value?.querySelectorAll?.("[data-glide-key]") ?? [])];

  watch(
    formation,
    () => {
      if (!enabled()) {
        first = null;
        figures().forEach(clearGlide);
        return;
      }
      first = new Map(figures().map((el) => [el.getAttribute("data-glide-key"), rectOf(el)]));
    },
    { flush: "pre" },
  );

  watch(
    formation,
    (next, prev) => {
      const captured = first;
      first = null;
      if (!captured || !enabled()) return;
      const crossing = !next !== !prev;
      const current = figures().filter((el) => !el.closest(LEAVING));
      // The height every persisting figure showed before the commit (they
      // share it): the reference an appearing figure starts from.
      const persisting = current
        .map((el) => captured.get(el.getAttribute("data-glide-key")))
        .find((rect) => rect && rect.height > 0);
      const referenceHeight = persisting?.height ?? 0;
      const plays = [];
      for (const el of current) {
        const key = el.getAttribute("data-glide-key");
        const known = captured.get(key);
        if (!crossing && known) continue; // the slot's own transition glides it
        const slot = el.parentElement;
        if (crossing && slot) slot.style.transition = "none";
        el.style.transition = "none";
        el.style.transform = "";
        const inverse = invertBox(rectOf(el), crossing ? known : null, referenceHeight);
        if (!inverse) {
          if (crossing && slot) plays.push({ el, slot, inverse: null });
          continue;
        }
        el.style.transformOrigin = inverse.origin;
        el.style.transform = inverse.transform;
        plays.push({ el, slot: crossing ? slot : null, inverse });
      }
      if (!plays.length) return;
      // One reflow commits every inverted box, then all release together.
      void rootRef.value?.offsetWidth;
      for (const { el, slot, inverse } of plays) {
        if (slot) slot.style.transition = "";
        if (!inverse) {
          clearGlide(el);
          continue;
        }
        let timer = 0;
        const token = {};
        el.__formationGlide = token;
        const done = (event) => {
          if (event && (event.target !== el || event.propertyName !== "transform")) return;
          clearTimeout(timer);
          el.removeEventListener("transitionend", done);
          el.removeEventListener("transitioncancel", done);
          // A newer glide may own the element by now; only clear our own.
          if (el.__formationGlide === token) {
            el.__formationGlide = null;
            clearGlide(el);
          }
        };
        el.addEventListener("transitionend", done);
        el.addEventListener("transitioncancel", done);
        timer = setTimeout(done, CLEANUP_MS);
        el.style.transition = GLIDE_TRANSITION;
        el.style.transform = "";
      }
    },
    { flush: "post" },
  );
}
