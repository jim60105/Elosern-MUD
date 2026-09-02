import { createApp } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "./AppClient.vue";
import { useElosernStore } from "./stores/elosern.js";
import { createWindowBridge } from "./bridge.js";
import { wireTransport } from "./transport.js";
import LayoutStore from "./lib/layout_store.js";
import "./styles/tokens.css";
import "./styles/fonts.css";
import "./styles/app-shell.css";

// C3 (webclient-vue-09-wire-transport-mount): the store-bound live renderers
// (design D3). The Vue app mounts AppClient — the store-driven root that
// binds the B-wave components to the C1 store, plus the live evennia.js
// transport binding. The C2 bridge replaces the transient window.ElosernVue
// surface with the window.Elosern.* public façades over the same imported
// modules.

function resolveMountPoint() {
  const host = document.getElementById("main-sub") ?? document.body;
  let point = document.getElementById("elosern-app");
  if (!point || !host.contains(point)) {
    point = document.createElement("div");
    point.id = "elosern-app";
    host.appendChild(point);
  }
  return point;
}

const pinia = createPinia();
setActivePinia(pinia);
const app = createApp(AppClient);
app.use(pinia);

// The bridge handle MUST exist before `app.mount()`: AppClient's onMounted
// callback (which registers the SceneBackdrop handle) runs during mount, so
// the `window.__elosernBridge` object must be in place before that callback
// fires, or its `if (bridge)` guard silently skips the registration.
const store = useElosernStore();
const bridge = createWindowBridge(store);

// Versioned browser persistence (webclient-desktop-shell:
// browser-persistence-is-versioned-and-presentation-only): on mount, read the
// stored `elosern.layout` wrapper, migrate a known prior version, and reset a
// malformed, oversized, missing, stock, or unknown version to the version-1
// default while preserving every required component. `load()` re-persists a
// migrated or reset wrapper so the next load starts from the current version.
const layoutStore = LayoutStore.createStore({ storage: window.localStorage });
layoutStore.load();

// C3: the live evennia.js OOB transport is wired by base.html's Vue branch
// AFTER the D10 text console has attached, so this coordinator owns the
// shared lifecycle event names (the evennia emitter keeps one listener per
// name). The hook is a no-op if the bundle is blocked (degradation path).
window.__elosernTransportBind = (consoleHandle) => wireTransport(store, consoleHandle);

// Stable test hook (the repository's `__`-prefixed harness-hook convention,
// cf. __elosernWs / __elosernSent): the managed-browser check drives the
// bridge's façade entry points through this handle. The C4 harness re-map
// also reads the live keyboard-router instance (depth()/currentItem()/resetFramesToRoot via store)
// off this handle, so the full bridge handle (facade + store + router + the
// key-routing uninstall hook) is exposed.
window.__elosernBridge = {
  store,
  facade: bridge.facade,
  router: bridge.router,
  // The declarative-frame derivation seam (webclient-frame-resolver-registry):
  // resolves a frame descriptor against the committed state at call time.
  // Test seam only — the shipped dock still drives copy frames until the
  // cutover changes land.
  resolveFrame: (descriptor) => store.resolveFrame(descriptor),
  uninstall: bridge.uninstall,
  // Test hook: the SceneBackdrop instance (its exposed interface, with
  // setPriorImage). The root component (AppClient) registers its
  // SceneBackdrop template ref's value into this handle on mount, so the
  // managed-browser pending-scene journey can seed the client-local
  // prior-image memory. A plain property (not a getter): `app._instance`
  // is dev-only in Vue's production build, so the registration approach
  // works in every build.
  backdrop: null,
};

app.mount(resolveMountPoint());
