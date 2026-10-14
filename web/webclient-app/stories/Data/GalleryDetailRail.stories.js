import GalleryDetailRail from "../../components/GalleryDetailRail.vue";
import { galleryStoryModel } from "../gallery-fixtures.js";
const model = galleryStoryModel();
export default { title: "Data/GalleryDetailRail", component: GalleryDetailRail };
export const DefaultPortrait = { args: { panel: model, card: model.cards[0], capabilities: model.capabilities, warnings: model.binding_warnings } };
export const UnmatchedBinding = { args: { panel: model, card: model.cards[2], capabilities: model.capabilities, warnings: model.binding_warnings } };
export const Failed = { args: { panel: model, card: model.cards[7], capabilities: model.capabilities } };
export const OfficialEntry = { args: { panel: model, entry: model.official_entries[2], capabilities: model.capabilities, warnings: [] } };
