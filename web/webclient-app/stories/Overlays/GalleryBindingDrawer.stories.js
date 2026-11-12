import GalleryBindingDrawer from "../../components/GalleryBindingDrawer.vue";
import { galleryStoryModel } from "../gallery-fixtures-v4.js";
const model = galleryStoryModel();
export default { title: "Overlays/GalleryBindingDrawer", component: GalleryBindingDrawer };
export const OverlapWarnings = { args: { model, card: model.cards[0] } };
// A bound card whose binding has no committed warning entry.
export const Unmatched = { args: { model, card: { ...model.cards[2], binding_present: true, chips: ["防具", "自訂臉框"] } } };
