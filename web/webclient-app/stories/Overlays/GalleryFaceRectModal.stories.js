import GalleryFaceRectModal from "../../components/GalleryFaceRectModal.vue";
import { galleryStoryModel } from "../gallery-fixtures.js";
// The modal reads its exact original (and that original's committed rectangle)
// out of the row's own canonical descriptor, so the story model substitutes the
// descriptor's own resource URLs with committed fallback artwork the offline
// showcase can serve.
//
// The two transient states cannot be frozen by a static build: a *loading*
// frame needs a request that never settles, and the ruler's own failure needs
// the committed `/art/defaults/man.webp` to break. Both are covered
// deterministically by `tests/components/gallery_original_editors.test.js` and
// by the managed browser journeys instead.
const model = galleryStoryModel();
// The committed fallback values the story model itself substitutes, reused here
// so each frame stays a display substitution rather than a second wire shape.
const FALLBACK_RECT = { x: 0.3576, y: 0.02, w: 0.2847, h: 0.16 };

function broken(row) {
  const next = structuredClone(row);
  next.artwork.attempts[0].resource.url = "/art/missing-face-original.png";
  return next;
}

function recovered(row) {
  const next = structuredClone(row);
  const candidate = next.artwork.attempts[0].resource;
  // A repaired original is a different admitted identity with its own committed
  // rectangle: the editor re-seeds from that original, never from the broken one.
  candidate.resource_id = `${candidate.resource_id}.repaired`;
  candidate.url = "/art/defaults/man.webp";
  candidate.geometry.face_rect = { ...FALLBACK_RECT };
  return next;
}

function silhouetteOnly(row) {
  const next = structuredClone(row);
  // A row that admits only the subject's silhouette terminal: it is a display
  // substitute, never an editable original.
  next.artwork.attempts = [];
  return next;
}

export default { title: "Overlays/GalleryFaceRectModal", component: GalleryFaceRectModal };
export const EditPortrait = { args: { panel: model, card: model.cards[0] } };
export const Rejected = { args: { panel: model, card: model.cards[0], rejected: true } };
// The broken exact original is removed with its crop preview, and the editor
// keeps a persistent explanation with the save disabled.
export const FailedOriginal = { args: { panel: model, card: broken(model.cards[0]) } };
// A repaired exact original decodes again: the editor seeds from that
// original's own rectangle and the save returns.
export const RecoveredOriginal = { args: { panel: model, card: recovered(model.cards[0]) } };
// Nothing to measure: the silhouette is never an edit target.
export const SilhouetteOnly = { args: { panel: model, card: silhouetteOnly(model.cards[0]) } };
