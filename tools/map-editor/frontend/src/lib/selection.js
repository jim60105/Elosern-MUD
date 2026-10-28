// None/single/multi selection over qualified references. A plain choice
// replaces the selection, a toggle (Ctrl/⌘) adds or removes one reference, and
// a range (Shift) spans the object list from the last chosen reference.

export function nextSelection(current, ref, { toggle = false, range = false, order = [] } = {}) {
  const list = [...(current ?? [])];
  if (!ref) return [];
  if (range && list.length) {
    const anchor = list[list.length - 1];
    const from = order.indexOf(anchor);
    const to = order.indexOf(ref);
    if (from >= 0 && to >= 0) {
      const span = from <= to ? order.slice(from, to + 1) : order.slice(to, from + 1).reverse();
      const kept = list.filter((item) => !span.includes(item));
      return [...kept, ...span];
    }
  }
  if (toggle) {
    return list.includes(ref) ? list.filter((item) => item !== ref) : [...list, ref];
  }
  return [ref];
}
