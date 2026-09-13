import GalleryFaceRectModal from "../../components/GalleryFaceRectModal.vue";
import { galleryStoryModel } from "../gallery-fixtures.js";
export default { title: "Overlays/GalleryFaceRectModal", component: GalleryFaceRectModal };
export const EditPortrait = { args: { card: galleryStoryModel().cards[0] } };
export const Rejected = { args: { card: galleryStoryModel().cards[0], rejected: true } };
