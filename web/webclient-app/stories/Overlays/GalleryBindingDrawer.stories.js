import GalleryBindingDrawer from "../../components/GalleryBindingDrawer.vue";
import { galleryStoryModel } from "../gallery-fixtures.js";
const model = galleryStoryModel();
export default { title: "Overlays/GalleryBindingDrawer", component: GalleryBindingDrawer };
export const OverlapWarnings = { args: { model, card: model.cards[0] } };
export const Unmatched = { args: { model, card: model.cards[2] } };
