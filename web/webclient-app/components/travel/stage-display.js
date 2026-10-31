// The one stage-display mapping of the travel stage (OpenSpec change
// wilderness-travel-leg-ui): how a canonical fatigue stage is drawn as a leg
// gauge tick and, once planning-ui draws a route, as a TravelMap route step
// mark (TravelGlyph `route` states). Pure; it never derives a stage.
//
// The four display buckets are the awake stages. The terminal `forced_sleep`
// (an admitted exact-zero arrival) and `sleeping` are drawn in the severe
// bucket with the sleep crescent; the canonical stage itself is preserved by
// every caller, never rewritten.

export const STAGE_BUCKETS = Object.freeze(["normal", "light", "moderate", "severe"]);

/** The short legend word of each display bucket. */
export const BUCKET_LABELS = Object.freeze({
  normal: "充沛",
  light: "輕度",
  moderate: "中度",
  severe: "重度",
});

const SLEEP_STAGES = new Set(["forced_sleep", "sleeping"]);

/**
 * `{ bucket, sleep }` for one canonical stage: `bucket` is one of
 * STAGE_BUCKETS and `sleep` marks the terminal sleep stages. An unknown
 * stage reads as null, never as a guessed bucket.
 */
export function stageDisplay(stage) {
  if (STAGE_BUCKETS.includes(stage)) return Object.freeze({ bucket: stage, sleep: false });
  if (SLEEP_STAGES.has(stage)) return Object.freeze({ bucket: "severe", sleep: true });
  return null;
}

/** The bucket's rank (0 = normal … 3 = severe), or -1 for an unknown bucket. */
export function bucketRank(bucket) {
  return STAGE_BUCKETS.indexOf(bucket);
}
