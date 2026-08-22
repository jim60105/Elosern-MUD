import { createApp } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "./AppClient.vue";
import { useElosernStore } from "./stores/elosern.js";
import { createWindowBridge } from "./bridge.js";
import { wireTransport } from "./transport.js";
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
app.mount(resolveMountPoint());

const store = useElosernStore();
const bridge = createWindowBridge(store);

// C3: the live evennia.js OOB transport is wired by base.html's Vue branch
// AFTER the D10 text console has attached, so this coordinator owns the
// shared lifecycle event names (the evennia emitter keeps one listener per
// name). The hook is a no-op if the bundle is blocked (degradation path).
window.__elosernTransportBind = (consoleHandle) => wireTransport(store, consoleHandle);

// Stable test hook (the repository's `__`-prefixed harness-hook convention,
// cf. __elosernWs / __elosernSent): the managed-browser check drives the
// bridge's façade entry points through this handle. The C4 harness re-map
// also reads the live keyboard-router instance (depth()/currentItem()/reset())
// off this handle, so the full bridge handle (facade + store + router + the
// key-routing uninstall hook) is exposed.
window.__elosernBridge = {
  store,
  facade: bridge.facade,
  router: bridge.router,
  uninstall: bridge.uninstall,
};
