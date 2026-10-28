// Continent layers (frontend design §4.1). Visibility is a view preference
// only: hiding a layer never changes a document. Every continent drawable
// names its layer; the partition layer holds derived, read-only output (the
// national borders; partition districts are drawn by the partition jobs).

export const CONTINENT_LAYERS = Object.freeze([
  { key: "terrain", label: "地形與通行", visible: true },
  { key: "water", label: "水系", visible: true },
  { key: "ridge", label: "山脊・隘口・渡口", visible: true },
  { key: "locations", label: "地點", visible: true },
  { key: "footprint", label: "據點佔地", visible: false },
  { key: "partition", label: "分區（衍生・唯讀）", visible: true },
]);

export function defaultHiddenLayers() {
  return CONTINENT_LAYERS.filter((layer) => !layer.visible).map((layer) => layer.key);
}

export function layerLabel(key) {
  return CONTINENT_LAYERS.find((layer) => layer.key === key)?.label ?? key;
}

const SHAPE_LAYERS = { land: "terrain", forest: "terrain", water: "water" };
const MARK_LAYERS = { location: "locations" };

export function layerOf(item) {
  return item.layer ?? SHAPE_LAYERS[item.role] ?? MARK_LAYERS[item.kind] ?? null;
}

// The scene with every drawable of a hidden continent layer left out.
export function visibleScene(scene, hidden) {
  if (!scene || scene.kind !== "continent" || !hidden?.length) return scene;
  const off = new Set(hidden);
  const keep = (item) => !off.has(layerOf(item));
  return {
    ...scene,
    shapes: scene.shapes.filter(keep),
    marks: scene.marks.filter(keep),
    links: scene.links.filter(keep),
    items: scene.items?.filter(keep),
    raster: scene.raster && keep(scene.raster) ? scene.raster : null,
  };
}
