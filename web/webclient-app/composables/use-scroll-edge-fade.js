// The scroll-edge fade of an over-tall scroll box
// (map-column-instrument-geometry design D5).
//
// The stage's `map` column hides its scrollbar; while content lies beyond its
// top or bottom edge, that edge fades out instead. This composable reports
// which edges have content beyond them. The column mounts and unmounts
// children (and they change height) without any scroll event, so the state
// is measured from scroll events, a ResizeObserver on the box and each of
// its children, and a MutationObserver that re-observes the children when
// one mounts or unmounts. Where an observer is absent (jsdom), only the
// scroll listener and the initial measure run.
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

// Pure: which edges of a scroll box have content beyond them. 1px of
// tolerance absorbs sub-pixel scroll positions.
export function scrollEdges({ scrollTop, clientHeight, scrollHeight }) {
  return {
    above: scrollTop > 1,
    below: scrollTop + clientHeight < scrollHeight - 1,
  };
}

// Reactive: `{ moreAbove, moreBelow }` refs for the element in `elRef`.
export function useScrollEdgeFade(elRef) {
  const moreAbove = ref(false);
  const moreBelow = ref(false);
  let attached = null;
  let resize = null;
  let mutation = null;

  function measure() {
    const el = elRef.value;
    if (!el) {
      moreAbove.value = false;
      moreBelow.value = false;
      return;
    }
    const { above, below } = scrollEdges(el);
    moreAbove.value = above;
    moreBelow.value = below;
  }

  // Observe the box and every current child afresh, so a child mounted
  // after setup is observed and an unmounted one is released.
  function observeChildren() {
    if (!resize || !attached) {
      return;
    }
    resize.disconnect();
    resize.observe(attached);
    for (const child of attached.children) {
      resize.observe(child);
    }
  }

  function detach() {
    attached?.removeEventListener("scroll", measure);
    resize?.disconnect();
    mutation?.disconnect();
    attached = null;
    resize = null;
    mutation = null;
  }

  function attach() {
    const el = elRef.value;
    // onMounted and the post-flush ref watch may both report one element.
    if (el && el === attached) {
      measure();
      return;
    }
    detach();
    if (el) {
      attached = el;
      el.addEventListener("scroll", measure, { passive: true });
      if (typeof ResizeObserver !== "undefined") {
        resize = new ResizeObserver(measure);
        observeChildren();
      }
      if (typeof MutationObserver !== "undefined") {
        mutation = new MutationObserver(() => {
          observeChildren();
          measure();
        });
        mutation.observe(el, { childList: true });
      }
    }
    measure();
  }

  onMounted(attach);
  watch(elRef, attach, { flush: "post" });
  onBeforeUnmount(detach);

  return { moreAbove, moreBelow };
}
