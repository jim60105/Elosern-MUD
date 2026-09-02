// Stable JSON with sorted keys: content comparison that is insensitive to
// key order, so committed panels can be compared across reducer commits. A
// `seen` set makes it safe on the reactive (proxied) view objects: a cycle
// is rendered as `~` instead of recursing forever.
//
// Shared by the store (the creation stage-resume and quantity-form panel
// comparisons) and the frame-resolver registry (the combat model's declared
// rebuild seam): one implementation, no duplicated balance of behavior.
export default function stableStringify(value, seen) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  seen = seen || new Set();
  if (seen.has(value)) {
    return "~";
  }
  seen.add(value);
  let s;
  if (Array.isArray(value)) {
    s = "[" + value.map((item) => stableStringify(item, seen)).join(",") + "]";
  } else {
    const keys = Object.keys(value).sort();
    s = "{" + keys.map((key) => JSON.stringify(key) + ":" + stableStringify(value[key], seen)).join(",") + "}";
  }
  seen.delete(value);
  return s;
}
