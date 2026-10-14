// Shared helpers for the scene surface's tests (change unified-scene-rendering).
//
// The backdrop renders image layers whose load/error observations ARE the
// loading core's input, so a test reaches a state by dispatching a real event
// on the element that owns the resource — with the natural dimensions the
// browser would report — instead of stubbing the driver. Nothing here reaches
// into component internals: every read goes through the DOM the component
// renders.

export function panelWithScene(scene, overrides = {}) {
  return {
    schema_version: 4,
    available: true,
    kind: "scene",
    scene,
    portrait_catalog: {},
    ...overrides,
  };
}

function layerFor(wrapper, url) {
  const layers = wrapper.findAll("img");
  const matches = layers.filter((img) => img.attributes("src") === url);
  if (!matches.length) {
    throw new Error(`no image layer renders ${url}: ${layers.map((img) => img.attributes("src"))}`);
  }
  // The displayed layer and a probe layer can share one URL only while the
  // element is promoted in place, so the first match is the element that owns
  // the resource.
  return matches[0];
}

function observe(wrapper, url, { width = 1536, height = 864 }) {
  const layer = layerFor(wrapper, url);
  Object.defineProperty(layer.element, "naturalWidth", { value: width, configurable: true });
  Object.defineProperty(layer.element, "naturalHeight", { value: height, configurable: true });
  return layer;
}

// Report one successful decode of the layer that carries `url`.
export async function observeLoad(wrapper, url, { width, height } = {}) {
  const layer = observe(wrapper, url, width === undefined ? {} : { width, height });
  await layer.trigger("load");
  await wrapper.vm.$nextTick();
}

// Report one failed load of the layer that carries `url`.
export async function observeError(wrapper, url) {
  const layer = layerFor(wrapper, url);
  await layer.trigger("error");
  await wrapper.vm.$nextTick();
}

// Report a decode failure: a load event whose image reports no pixels.
export async function observeDecodeFailure(wrapper, url) {
  const layer = layerFor(wrapper, url);
  Object.defineProperty(layer.element, "naturalWidth", { value: 0, configurable: true });
  Object.defineProperty(layer.element, "naturalHeight", { value: 0, configurable: true });
  await layer.trigger("load");
  await wrapper.vm.$nextTick();
}

// Every URL the wrapper currently renders, probe layers included: what the
// page is fetching or showing.
export function renderedUrls(wrapper) {
  return wrapper.findAll("img").map((img) => img.attributes("src"));
}

// The URLs the wrapper PRESENTS as the scene bitmap (the visible layer only).
export function displayedUrl(wrapper) {
  const image = wrapper.find('[data-testid="scene-backdrop-image"]');
  return image.exists() ? image.attributes("src") : null;
}
