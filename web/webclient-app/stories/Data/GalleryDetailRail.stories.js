import GalleryDetailRail from "../../components/GalleryDetailRail.vue";
import { galleryStoryModel } from "../gallery-fixtures.js";
const model = galleryStoryModel();
export default { title: "Data/GalleryDetailRail", component: GalleryDetailRail };
export const DefaultPortrait = { args: { card: model.cards[0], capabilities: model.capabilities, warnings: model.binding_warnings } };
export const UnmatchedBinding = { args: { card: model.cards[2], capabilities: model.capabilities, warnings: model.binding_warnings } };
export const Failed = { args: { card: model.cards[7], capabilities: model.capabilities } };
