import GalleryStageTransformModal from "../../components/GalleryStageTransformModal.vue";
import { galleryStoryModel } from "../gallery-fixtures.js";
// The modal edits one exact original's committed placement, so the story
// fixture carries the placement inside that row's canonical descriptor (the v3
// wire shape) rather than as a top-level card field.
//
// Two frames cannot be frozen by a static build and are covered
// deterministically by `tests/components/gallery_original_editors.test.js` and
// by the managed browser journeys instead: the transient *loading* frame (it
// needs a request that never settles) and the *ruler's own failure* (the
// offline showcase serves the committed `/art/defaults/man.webp` the ruler
// always observes, so it cannot be made to fail here).
const model = galleryStoryModel();
function card(stage = { scale: 1, x: 0, y: 0 }) {
  const row = structuredClone(model.cards[0]);
  row.artwork.attempts[0].resource.geometry.stage = { ...stage };
  return row;
}
function failedCard() {
  const row = card();
  row.artwork.attempts[0].resource.url = "/art/missing-stage-story.png";
  return row;
}
// A repaired exact original with its own placement: the editor shows the
// healthy frame again over the new original rather than staying failed.
function recoveredCard(stage = { scale: 0.6, x: 0.1, y: -0.2 }) {
  const row = card(stage);
  const candidate = row.artwork.attempts[0].resource;
  candidate.resource_id = `${candidate.resource_id}.repaired`;
  candidate.url = "/art/defaults/man.webp";
  return row;
}
export default { title: "Overlays/GalleryStageTransformModal", component: GalleryStageTransformModal };
export const Identity = { args: { panel: model, card: card() } };
export const Child = { args: { panel: model, card: card({ scale: 0.6, x: 0, y: 0 }) } };
export const Translated = { args: { panel: model, card: card({ scale: 0.6, x: 0.1, y: -0.2 }) } };
export const Boundary = { args: { panel: model, card: card({ scale: 2, x: 0.5, y: -0.5 }) } };
export const Pending = { args: { panel: model, card: card(), disabled: true } };
export const Rejected = { args: { panel: model, card: card({ scale: 0.6, x: 0.1, y: -0.2 }), rejected: true } };
// Only the healthy adult ruler remains beside the local failure explanation, and
// no save is possible.
export const FailedLoad = { args: { panel: model, card: failedCard() } };
export const RecoveredOriginal = { args: { panel: model, card: recoveredCard() } };
export const ReducedMotion = { args: { panel: model, card: card() }, parameters: { reducedMotion: "reduce" } };
