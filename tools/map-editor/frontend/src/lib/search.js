// Name and ID search over the object catalog. Every result carries its parent
// map and owning source document, and how many results share its label, so
// equal names in different maps are always told apart.

function rank(entry, needle) {
  const fields = [entry.label, entry.id, entry.ref].map((value) => String(value ?? "").toLowerCase());
  if (fields.some((value) => value === needle)) return 0;
  if (fields.some((value) => value.startsWith(needle))) return 1;
  if (fields.some((value) => value.includes(needle))) return 2;
  return null;
}

export function searchObjects(catalog, query, limit = 50) {
  const needle = String(query ?? "").trim().toLowerCase();
  if (!needle) return [];
  const found = [];
  let order = 0;
  for (const entry of catalog.values()) {
    const score = rank(entry, needle);
    if (score !== null) found.push({ entry, score, order });
    order += 1;
  }
  found.sort((a, b) => a.score - b.score || a.order - b.order);
  const results = found.slice(0, limit).map(({ entry }) => entry);
  const labels = new Map();
  for (const entry of results) labels.set(entry.label, (labels.get(entry.label) ?? 0) + 1);
  return results.map((entry) => ({ ...entry, sameLabel: labels.get(entry.label) }));
}
