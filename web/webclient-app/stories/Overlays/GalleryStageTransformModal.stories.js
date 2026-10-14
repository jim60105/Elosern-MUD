import GalleryStageTransformModal from "../../components/GalleryStageTransformModal.vue";
import { galleryStoryModel } from "../gallery-fixtures.js";
// The modal edits one exact original's committed placement, so the story
// fixture carries the placement inside that row's canonical descriptor (the v3
// wire shape) rather than as a top-level card field.
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
export default { title: "Overlays/GalleryStageTransformModal", component: GalleryStageTransformModal };
export const Identity = { args: { panel: model, card: card() } };
export const Child = { args: { panel: model, card: card({ scale: 0.6, x: 0, y: 0 }) } };
export const Translated = { args: { panel: model, card: card({ scale: 0.6, x: 0.1, y: -0.2 }) } };
export const Boundary = { args: { panel: model, card: card({ scale: 2, x: 0.5, y: -0.5 }) } };
export const Pending = { args: { panel: model, card: card(), disabled: true } };
export const Rejected = { args: { panel: model, card: card({ scale: 0.6, x: 0.1, y: -0.2 }), rejected: true } };
export const FailedLoad = { args: { panel: model, card: failedCard() } };
export const ReducedMotion = { args: { panel: model, card: card() }, parameters: { reducedMotion: "reduce" } };
