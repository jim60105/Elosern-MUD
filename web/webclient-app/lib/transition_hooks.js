// The leaving-element rule of the stage transitions (OpenSpec change
// webclient-scene-transitions, design D1; the AVG stage design §9.2).
//
// Every `<Transition>` the stage animates binds these hooks with
// `v-bind="inertWhileLeaving"`, so a leaving copy is outside the
// accessibility tree, the tab order, and pointer hit-testing from the patch
// that commits its removal until it is gone. `inert` does not move focus, so
// a surface that can hold focus rescues it first (the vitals island's
// pre-flush rescue); every other leaving copy holds no focusable element.
//
// Pure: no Vue import. Vue calls `onBeforeLeave` synchronously in the patch
// that removes the element, `onLeaveCancelled` when a `v-show` element is
// shown again mid-leave, and `onAfterLeave` once the leave has finished.
export const inertWhileLeaving = Object.freeze({
  onBeforeEnter(el) {
    el.inert = false;
  },
  onBeforeLeave(el) {
    el.inert = true;
  },
  onAfterLeave(el) {
    el.inert = false;
  },
  onLeaveCancelled(el) {
    el.inert = false;
  },
});
