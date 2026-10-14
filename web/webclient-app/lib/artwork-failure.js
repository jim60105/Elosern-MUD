// artwork-failure.js — the one shared mapping from a closed artwork reason code
// to bounded zh-TW category text.
//
// The reducer/driver and every renderer consume reason *codes*; only this
// module turns one into player-facing prose, so no surface ever prints a raw
// exception, filesystem path, credential, prompt or backend payload. The
// vocabulary is closed: an unknown code falls back to a generic bounded
// sentence instead of echoing the input.
//
// The categories split the two genuinely different local signals:
//   * a reached failure (an image the player should have seen is broken) —
//     error styling;
//   * an availability failure (a required panel could not supply data) —
//     availability styling.
// Expected absence and in-progress loading are deliberately absent from this
// map: they carry no error text and no error styling.

// Closed vocabulary from the shared descriptor contract. Each value is the
// single bounded category sentence rendered for that code.
export const ARTWORK_FAILURE_CATEGORIES = Object.freeze({
  generation_failed: "此圖片生成失敗。",
  generated_output_missing: "此圖片的生成結果已遺失。",
  source_unavailable: "此圖片的來源目前無法使用。",
  source_rejected: "此圖片的來源未通過檢查。",
  explicit_reference_missing: "指定的圖片不存在。",
  metadata_invalid: "此圖片的資料不完整。",
  required_resource_missing: "缺少必要的圖片資源。",
  configuration_invalid: "圖片設定有誤。",
  panel_unavailable: "圖片面板目前無法提供資料。",
  image_load_failed: "圖片載入失敗。",
  image_decode_failed: "圖片無法解碼。",
});

// The bounded sentence an unknown/absent code renders. Never the input itself.
export const ARTWORK_FAILURE_FALLBACK = "圖片無法顯示。";

// The availability failures use availability styling, not per-image error
// styling (the shared lifecycle distinguishes them).
export const ARTWORK_AVAILABILITY_FAILURE_REASONS = Object.freeze(["panel_unavailable"]);

export function isArtworkFailureReason(reason) {
  return typeof reason === "string" && Object.hasOwn(ARTWORK_FAILURE_CATEGORIES, reason);
}

export function isArtworkAvailabilityFailure(reason) {
  return ARTWORK_AVAILABILITY_FAILURE_REASONS.includes(reason);
}

// Bounded category text for a reason code. An unknown code yields the generic
// sentence; a null/undefined code yields the empty string (no claim at all).
export function artworkFailureCategory(reason) {
  if (reason === null || reason === undefined) {
    return "";
  }
  if (isArtworkFailureReason(reason)) {
    return ARTWORK_FAILURE_CATEGORIES[reason];
  }
  return ARTWORK_FAILURE_FALLBACK;
}
