import GalleryGenerateDrawer from "../../components/GalleryGenerateDrawer.vue";
import { GALLERY_V4_MONSTER as GALLERY_MONSTER, galleryStoryModel } from "../gallery-fixtures-v4.js";
export default { title: "Overlays/GalleryGenerateDrawer", component: GalleryGenerateDrawer };
export const Character = { args: { model: galleryStoryModel() } };
export const Monster = { args: { model: galleryStoryModel(GALLERY_MONSTER) } };
export const Rejected = { args: { model: galleryStoryModel(), rejected: true } };
