// The message window's hidden measurer (AVG stage design §6.2 step 2;
// webclient-message-window-component design D2).
//
// A hidden twin of the page surface decides whether a candidate page still
// fits: it carries the page's own classes (same font, width cap, and
// padding), renders the candidate fragments through the same
// `narrativeBlockNodes` the page renders with, and compares its height with
// the surface's. Capacity is measured pixel height, never a line count,
// because `sys` and map lines use other line heights.
//
// The composable also owns the two re-page triggers the layout gives:
// `boxKey` (a ResizeObserver on the surface) and `ready` (the
// `document.fonts.ready` gate; true at once where the Font Loading API is
// absent, as in jsdom).
import { h, onBeforeUnmount, onMounted, ref, render } from "vue";
import { narrativeBlockNodes } from "../lib/narrative_line_nodes.js";

// Sub-pixel slack: both heights are fractional layout boxes.
const FIT_SLACK_PX = 0.5;

export function useMessageMeasure(surfaceRef) {
  const ready = ref(false);
  const boxKey = ref("");
  let measurer = null;
  let observer = null;
  let disposed = false;

  function readBox() {
    const surface = surfaceRef.value;
    if (!surface) {
      return;
    }
    const rect = surface.getBoundingClientRect();
    boxKey.value = `${Math.round(rect.width)}x${Math.round(rect.height)}`;
  }

  onMounted(() => {
    const surface = surfaceRef.value;
    if (surface && surface.parentNode) {
      measurer = document.createElement("div");
      measurer.className = "message-window__page message-window__measure";
      measurer.setAttribute("aria-hidden", "true");
      surface.parentNode.appendChild(measurer);
    }
    readBox();
    if (surface && typeof ResizeObserver === "function") {
      observer = new ResizeObserver(() => readBox());
      observer.observe(surface);
    }
    const fonts = typeof document !== "undefined" ? document.fonts : undefined;
    if (!fonts || !fonts.ready || typeof fonts.ready.then !== "function") {
      ready.value = true;
    } else {
      fonts.ready.then(
        () => {
          if (!disposed) ready.value = true;
        },
        () => {
          if (!disposed) ready.value = true;
        },
      );
    }
  });

  onBeforeUnmount(() => {
    disposed = true;
    observer?.disconnect();
    observer = null;
    if (measurer) {
      render(null, measurer);
      measurer.remove();
      measurer = null;
    }
  });

  // Does this candidate page (an array of page fragments) fit the surface?
  // With no mounted surface there is nothing to measure against, so every
  // candidate fits (the caller only pages once mounted).
  function fits(fragments) {
    const surface = surfaceRef.value;
    if (!measurer || !surface) {
      return true;
    }
    render(
      h(
        "div",
        { class: "message-window__measure-flow" },
        fragments.map((fragment, index) => narrativeBlockNodes(fragment, index)),
      ),
      measurer,
    );
    return (
      measurer.getBoundingClientRect().height <=
      surface.getBoundingClientRect().height + FIT_SLACK_PX
    );
  }

  // Empties the measurer after a paging pass.
  function clear() {
    if (measurer) {
      render(null, measurer);
    }
  }

  return { ready, boxKey, fits, clear };
}
