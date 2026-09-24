// Composable for full-map fit view interaction (design D1–D4,
// openspec/changes/webclient-full-map-fit-view).
// Binds viewport ResizeObserver, mouse wheel zoom, pointer drag pan,
// focus reveal, and exposes zoomIn, zoomOut, recentre controls.
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  toValue,
  watch,
} from "vue";
import {
  DRAG_THRESHOLD,
  FIT_INSET,
  ZOOM_STEP,
  centreOn,
  clampView,
  fitView,
  panBy,
  resizeView,
  revealBox,
  scaleBounds,
  viewBoxOf,
  zoomAt,
} from "../lib/map_view.js";
import { HALO_R } from "./use-map-lattice-geometry.js";

export function useMapView({
  enabled = true,
  canvasWidth,
  canvasHeight,
  currentPos,
  nodePos,
  currentNodeId,
  viewportEl,
  markerScale = 1,
  labelFont = 11,
}) {
  const view = ref(null);
  const isDragging = ref(false);
  let lastFrame = null;
  let pointerStart = null;
  let lastPointer = null;
  let suppressClick = false;

  function getFrame() {
    const el = toValue(viewportEl);
    const W = toValue(canvasWidth);
    const H = toValue(canvasHeight);
    if (!el || !W || !H) return null;
    const rect = el.getBoundingClientRect();
    const vw = rect.width;
    const vh = rect.height;
    if (vw <= 2 * FIT_INSET || vh <= 2 * FIT_INSET) return null;
    return { vw, vh, W, H };
  }

  // Viewport resize observer (guarded for jsdom)
  const observer =
    typeof ResizeObserver !== "undefined"
      ? new ResizeObserver((entries) => {
          if (!toValue(enabled)) return;
          for (const entry of entries) {
            const cr = entry.contentRect;
            const vw = cr.width;
            const vh = cr.height;
            const W = toValue(canvasWidth);
            const H = toValue(canvasHeight);
            if (!W || !H || vw <= 2 * FIT_INSET || vh <= 2 * FIT_INSET) continue;

            const newFrame = { vw, vh, W, H };
            if (!view.value) {
              view.value = fitView(newFrame);
            } else if (lastFrame) {
              view.value = resizeView(view.value, lastFrame, newFrame);
            } else {
              view.value = fitView(newFrame);
            }
            lastFrame = newFrame;
          }
        })
      : null;

  onMounted(() => {
    const el = toValue(viewportEl);
    if (el && observer) {
      observer.observe(el);
    }
  });

  watch(
    () => toValue(viewportEl),
    (el, oldEl) => {
      if (oldEl && observer) observer.unobserve(oldEl);
      if (el && observer) observer.observe(el);
    },
  );

  onBeforeUnmount(() => {
    observer?.disconnect();
  });

  // Defensive: a live enabled→disabled flip (no product surface does this)
  // must not strand the drag gesture or the grabbing cursor.
  watch(
    () => toValue(enabled),
    (on) => {
      if (!on) {
        pointerStart = null;
        lastPointer = null;
        isDragging.value = false;
      }
    },
  );

  // Payload update watcher (design D4)
  watch(
    [
      () => toValue(canvasWidth),
      () => toValue(canvasHeight),
      () => toValue(currentNodeId),
    ],
    ([newW, newH, newId], [oldW, oldH, oldId]) => {
      if (!toValue(enabled) || !view.value) return;
      const f = getFrame();
      if (!f) return;

      if (view.value.fitted) {
        view.value = fitView(f);
      } else if (newId !== oldId && toValue(currentPos)) {
        view.value = centreOn(view.value, toValue(currentPos), f);
      } else {
        view.value = clampView(view.value, f);
      }
    },
  );

  const canZoomIn = computed(() => {
    if (!toValue(enabled) || !view.value) return false;
    const f = getFrame();
    if (!f) return false;
    const bounds = scaleBounds(f);
    return view.value.s < bounds.max - 1e-4;
  });

  const canZoomOut = computed(() => {
    if (!toValue(enabled) || !view.value) return false;
    const f = getFrame();
    if (!f) return false;
    const bounds = scaleBounds(f);
    return view.value.s > bounds.min + 1e-4;
  });

  const canRecentre = computed(() => {
    if (!toValue(enabled) || !view.value) return false;
    return !!toValue(currentPos);
  });

  function zoomIn() {
    if (!toValue(enabled) || !view.value) return;
    const f = getFrame();
    if (!f) return;
    view.value = zoomAt(view.value, ZOOM_STEP, { x: f.vw / 2, y: f.vh / 2 }, f);
  }

  function zoomOut() {
    if (!toValue(enabled) || !view.value) return;
    const f = getFrame();
    if (!f) return;
    view.value = zoomAt(view.value, 1 / ZOOM_STEP, { x: f.vw / 2, y: f.vh / 2 }, f);
  }

  function recentre() {
    if (!toValue(enabled) || !view.value) return;
    const pos = toValue(currentPos);
    if (!pos) return;
    const f = getFrame();
    if (!f) return;
    view.value = centreOn(view.value, pos, f);
  }

  function onWheel(event) {
    if (!toValue(enabled) || !view.value) return;
    // Consumed whenever the fit view owns this viewport, even at a zoom
    // bound (design D3): prevent before any further bail-out so the page
    // never scrolls behind the map. When disabled (the island), the event
    // passes through untouched.
    event.preventDefault();
    const f = getFrame();
    if (!f) return;

    let dy = event.deltaY;
    if (event.deltaMode === 1) {
      dy *= 16;
    } else if (event.deltaMode === 2) {
      dy *= f.vh;
    }
    let factor = Math.exp(-dy * 0.0015);
    factor = Math.max(0.5, Math.min(2, factor));

    const el = toValue(viewportEl);
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const anchorPx = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };

    view.value = zoomAt(view.value, factor, anchorPx, f);
  }

  function onPointerDown(event) {
    // The drag gesture is tracked from the enabled flag alone: the click
    // suppression it arms is a gesture concern, independent of whether the
    // viewport has measured a box yet.
    if (!toValue(enabled)) return;
    if (event.button !== 0) return;

    pointerStart = { x: event.clientX, y: event.clientY, id: event.pointerId };
    lastPointer = { x: event.clientX, y: event.clientY };
    isDragging.value = false;
  }

  function onPointerMove(event) {
    if (!toValue(enabled) || !pointerStart) return;
    if (event.pointerId !== pointerStart.id) return;

    if (!isDragging.value) {
      const dist = Math.hypot(
        event.clientX - pointerStart.x,
        event.clientY - pointerStart.y,
      );
      if (dist > DRAG_THRESHOLD) {
        isDragging.value = true;
        const el = toValue(viewportEl);
        try {
          el?.setPointerCapture?.(event.pointerId);
        } catch (_) {}
      }
    }

    if (isDragging.value) {
      const f = getFrame();
      if (f && lastPointer) {
        const dx = event.clientX - lastPointer.x;
        const dy = event.clientY - lastPointer.y;
        view.value = panBy(view.value, dx, dy, f);
      }
      lastPointer = { x: event.clientX, y: event.clientY };
    }
  }

  function onPointerUp(event) {
    if (!pointerStart || event.pointerId !== pointerStart.id) return;
    const el = toValue(viewportEl);
    if (isDragging.value) {
      try {
        el?.releasePointerCapture?.(event.pointerId);
      } catch (_) {}
      suppressClick = true;
      setTimeout(() => {
        suppressClick = false;
      }, 0);
      isDragging.value = false;
    }
    pointerStart = null;
    lastPointer = null;
  }

  function onPointerCancel(event) {
    if (!pointerStart || event.pointerId !== pointerStart.id) return;
    const el = toValue(viewportEl);
    if (isDragging.value) {
      try {
        el?.releasePointerCapture?.(event.pointerId);
      } catch (_) {}
      isDragging.value = false;
    }
    pointerStart = null;
    lastPointer = null;
  }

  function onClickCapture(event) {
    if (suppressClick) {
      event.stopPropagation();
      event.preventDefault();
      suppressClick = false;
    }
  }

  function onFocusIn(event) {
    if (!toValue(enabled) || !view.value) return;
    const target = event.target?.closest?.("[data-node]");
    if (!target) return;
    const nodeId =
      target.getAttribute("data-node") || target.getAttribute("data-node-id");
    if (!nodeId) return;

    const pos = typeof nodePos === "function" ? nodePos(nodeId) : null;
    if (!pos) return;

    const mScale = toValue(markerScale) ?? 1;
    const lFont = toValue(labelFont) ?? 11;
    const labelBaseline =
      lFont === 11 ? 13 * mScale + 13 : 11 * mScale + 2 + lFont;

    const box = {
      left: pos.x - HALO_R * mScale,
      right: pos.x + HALO_R * mScale,
      top: pos.y - HALO_R * mScale,
      bottom: pos.y + labelBaseline + lFont,
    };

    const f = getFrame();
    if (f) {
      view.value = revealBox(view.value, box, 24, f);
    }
  }

  const viewBox = computed(() => {
    const W = toValue(canvasWidth) ?? 0;
    const H = toValue(canvasHeight) ?? 0;
    if (!toValue(enabled) || !view.value) {
      return `0 0 ${W} ${H}`;
    }
    const f = getFrame();
    if (!f) {
      return `0 0 ${W} ${H}`;
    }
    return viewBoxOf(view.value, f);
  });

  return {
    view,
    viewBox,
    canZoomIn,
    canZoomOut,
    canRecentre,
    isDragging,
    zoomIn,
    zoomOut,
    recentre,
    onWheel,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onPointerCancel,
    onClickCapture,
    onFocusIn,
  };
}
