// Authored world-data model (gm-portal-s4-world-data §4/§5).
//
// One place owns the world-data route names, the request paths, the
// registry-entry link targets and the field-path convention shared with the
// backend reference walk (``stages[0].objective.species_key``). Every request
// goes through the single fetch boundary (lib/api.js); nothing here caches
// server state.

//: The route names the world-data pages register (router.js).
export const WORLD_ROUTE = Object.freeze({
  home: "world-home",
  registry: "world-registry",
  entry: "world-entry",
  source: "world-source",
});

//: The glyph that marks an authored-entry link (runtime objects use ▸).
export const AUTHORED_GLYPH = "◇";

//: Copy shared by every page's provenance note.
export const PROVENANCE_COPY = Object.freeze({
  loaded: "此處顯示伺服器目前載入的資料。修改請編輯原始檔，並重新啟動伺服器後生效。",
  disk: "此為磁碟上的檔案內容，不一定是伺服器目前載入的版本。規則書的修改需重新啟動伺服器才會生效。",
  reloadable: "提示詞是例外：可在此重新載入記憶體中的提示詞庫，不必重新啟動伺服器，也不會變更任何世界狀態。",
});

//: Source groups in display order with their labels.
export const SOURCE_GROUPS = Object.freeze([
  Object.freeze({ key: "rulebook", label: "規則書" }),
  Object.freeze({ key: "commerce", label: "規則書／商業" }),
  Object.freeze({ key: "prompts", label: "提示詞" }),
]);

// --- request paths ---------------------------------------------------------

function segment(value) {
  return encodeURIComponent(String(value ?? ""));
}

/** A slash-separated name (a source name) with each segment encoded. */
function segments(value) {
  return String(value ?? "")
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
}

export function inventoryPath() {
  return "/registry/";
}

export function searchPath(query) {
  return `/registry/?q=${encodeURIComponent(String(query ?? ""))}`;
}

export function registryListPath(registry, { cursor = null, limit = null, q = "" } = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", String(q));
  if (limit) params.set("limit", String(limit));
  if (cursor) params.set("cursor", String(cursor));
  const query = params.toString();
  return `/registry/${segment(registry)}${query ? `?${query}` : ""}`;
}

export function entryPath(registry, key) {
  return `/registry/${segment(registry)}/${segment(key)}`;
}

export function sourcesPath() {
  return "/sources/";
}

export function sourcePath(name) {
  return `/sources/${segments(name)}`;
}

export const PROMPT_RELOAD_PATH = "/sources/prompts/reload";

// --- router locations --------------------------------------------------------

export function registryTarget(registry, query = {}) {
  return { name: WORLD_ROUTE.registry, params: { registry: String(registry) }, query };
}

export function entryTarget(registry, key) {
  return { name: WORLD_ROUTE.entry, params: { registry: String(registry), key: String(key) }, query: {} };
}

export function sourceTarget(name) {
  return { name: WORLD_ROUTE.source, params: { name: String(name).split("/") }, query: {} };
}

/** A real href for a world-data router location (modified clicks, no router). */
export function worldHref(target, base = "/gm/") {
  if (!target) return null;
  const query = new URLSearchParams(target.query ?? {}).toString();
  const suffix = query ? `?${query}` : "";
  if (target.name === WORLD_ROUTE.home) return `${base}world${suffix}`;
  if (target.name === WORLD_ROUTE.registry) return `${base}world/${segment(target.params.registry)}${suffix}`;
  if (target.name === WORLD_ROUTE.entry) {
    return `${base}world/${segment(target.params.registry)}/${segment(target.params.key)}${suffix}`;
  }
  if (target.name === WORLD_ROUTE.source) {
    const name = Array.isArray(target.params.name) ? target.params.name.join("/") : target.params.name;
    return `${base}world/sources/${segments(name)}${suffix}`;
  }
  return null;
}

/** The router location of a ``{"kind": "registry", ...}`` link descriptor. */
export function registryLinkTarget(link) {
  if (!link || link.kind !== "registry" || !link.registry || link.id === null || link.id === undefined) return null;
  const key = String(link.id);
  if (!key) return null;
  return entryTarget(link.registry, key);
}

/** Read a route param that may arrive as a repeated (array) segment. */
export function joinParam(value) {
  return Array.isArray(value) ? value.join("/") : String(value ?? "");
}

// --- field paths --------------------------------------------------------------

/** The child path of one JSON node (the backend's field_path shape). */
export function childPath(parent, key) {
  if (typeof key === "number") return `${parent}[${key}]`;
  return parent ? `${parent}.${key}` : String(key);
}

/** ``field_path -> link descriptor`` for the references of one entry. */
export function referenceLinks(references = []) {
  const links = {};
  for (const reference of references) {
    links[reference.field_path] = {
      kind: "registry",
      registry: reference.registry,
      id: reference.key,
      label: reference.key,
      missing: !reference.exists,
    };
  }
  return links;
}

/** Group sorted search hits by registry, keeping the server order. */
export function groupHits(items = []) {
  const groups = [];
  let current = null;
  for (const item of items) {
    if (!current || current.registry !== item.registry) {
      current = { registry: item.registry, keys: [] };
      groups.push(current);
    }
    current.keys.push(item.key);
  }
  return groups;
}
