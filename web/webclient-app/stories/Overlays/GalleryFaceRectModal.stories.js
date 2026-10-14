import GalleryFaceRectModal from "../../components/GalleryFaceRectModal.vue";
import { galleryStoryModel } from "../gallery-fixtures.js";
const model = galleryStoryModel();
export default { title: "Overlays/GalleryFaceRectModal", component: GalleryFaceRectModal };
export const EditPortrait = { args: { panel: model, card: model.cards[0] } };
export const Rejected = { args: { panel: model, card: model.cards[0], rejected: true } };
