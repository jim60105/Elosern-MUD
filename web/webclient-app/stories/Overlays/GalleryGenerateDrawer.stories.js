import GalleryGenerateDrawer from "../../components/GalleryGenerateDrawer.vue";
import { GALLERY_V4_MONSTER as GALLERY_MONSTER, galleryStoryModel } from "../gallery-fixtures-v4.js";
import { CREATION_PORTRAIT_STATES } from "../fixtures.js";
import { CREATION_DRAWER_MODEL } from "../../composables/use-creation-portrait.js";
export default { title: "Overlays/GalleryGenerateDrawer", component: GalleryGenerateDrawer };
export const Character = { args: { model: galleryStoryModel() } };
export const Monster = { args: { model: galleryStoryModel(GALLERY_MONSTER) } };
export const Rejected = { args: { model: galleryStoryModel(), rejected: true } };

// creation-draft-portrait: the same drawer in creation context — the
// free-text-only view model, creation copy, no equipment or character link.
const READY = CREATION_PORTRAIT_STATES.ready.artwork;
export const CreationContext = { args: { model: CREATION_DRAWER_MODEL, context: "creation" } };
export const CreationRegenerate = {
  args: { model: CREATION_DRAWER_MODEL, context: "creation", preview: { artwork: READY, image_id: READY.generation_subject, label: "林楓的肖像" } },
};
export const CreationRejected = { args: { model: CREATION_DRAWER_MODEL, context: "creation", rejected: true } };
// Server unavailability: submit disabled, prompt editable, refresh offered.
export const CreationUnavailable = {
  args: { model: CREATION_DRAWER_MODEL, context: "creation", unavailableReason: CREATION_PORTRAIT_STATES.unavailable.reason },
};
