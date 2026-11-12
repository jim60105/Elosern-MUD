import GalleryDetailRail from "../../components/GalleryDetailRail.vue";
import { galleryStoryModel } from "../gallery-fixtures-v4.js";
const model = galleryStoryModel();
export default { title: "Data/GalleryDetailRail", component: GalleryDetailRail };
export const DefaultPortrait = { args: { panel: model, card: model.cards[0], capabilities: model.capabilities, warnings: model.binding_warnings } };
// A bound card whose binding has no committed warning entry.
const unmatched = { ...model.cards[2], binding_present: true, chips: ["防具", "自訂臉框"] };
export const UnmatchedBinding = { args: { panel: model, card: unmatched, capabilities: model.capabilities, warnings: model.binding_warnings } };
export const Failed = { args: { panel: model, card: model.cards.find((row) => row.status === "failed"), capabilities: model.capabilities } };
export const OfficialEntry = { args: { panel: model, entry: model.official_entries.find((row) => row.is_current), capabilities: model.capabilities, warnings: [] } };
