import ArtworkPreview from "../../components/ArtworkPreview.vue";
import { galleryStoryModel } from "../gallery-fixtures.js";

// ArtworkPreview is the shared descriptor position: one canonical descriptor in,
// the exact original or the subject's silhouette out. The story model remaps the
// descriptor's own resources onto committed artwork because the offline static
// server serves no /art/gallery or /art/official route.
const model = galleryStoryModel();
const panel = { available: true };
const row = model.cards[0];

function withFault(descriptor) {
  const next = structuredClone(descriptor);
  next.attempts = [{
    type: "fault",
    source_id: next.attempts[0].source_id,
    rank: 10,
    reason: "generated_output_missing",
  }];
  next.retention_sources = [];
  return next;
}

export default { title: "Core/ArtworkPreview", component: ArtworkPreview };
export const LoadedOriginal = {
  args: { artwork: row.artwork, panel, alt: "肖像，已載入的原圖" },
};
export const SilhouetteFallback = {
  args: { artwork: withFault(row.artwork), panel, alt: "肖像，替代剪影" },
};
export const UnavailablePanel = {
  args: { artwork: row.artwork, panel: { available: false }, alt: "肖像，面板無法使用" },
};
export const ExpectedAbsent = {
  args: { artwork: null, panel, required: false, alt: "肖像，此模式不需要" },
};
