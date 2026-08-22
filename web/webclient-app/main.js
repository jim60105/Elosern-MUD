import { createApp } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppShell from "./components/AppShell.vue";
import { useElosernStore } from "./stores/elosern.js";
import { createWindowBridge } from "./bridge.js";
import "./styles/tokens.css";
import "./styles/fonts.css";
import "./styles/app-shell.css";

// B1 (webclient-vue-02-showcase-core): the core narrative family is the live
// app root. The mount target is a dedicated #elosern-app container created
// inside #main-sub so the stock #messagewindow fallback survives the Vue
// mount (Vue clears its mount container's children) and is retired by the
// shell instead — hidden, never removed, so C3 can re-activate the degraded
// text path. The C2 bridge replaces this transient window.ElosernVue surface
// with the window.Elosern.* public façades over the same imported modules.

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

// B1 (offline, mock-driven, design D3): the mounted shell starts in the
// usable "ready" slice so every required core surface is visible and usable
// at the supported viewports; the pre-connection splash states
// (connecting/waiting/offline) are showcase states owned by the
// ConnectOverlay stories and component tests until the C1 store drives the
// live status slice.

// C1 (webclient-vue-07-wire-store) + C2 (webclient-vue-08-wire-bridge-
// contracts): the C1 store is the single writer of client view state; the
// C2 browser-bridge re-exposes the window.Elosern.* public façades over the
// store and the imported UMD modules (design D5: single transport seam, one
// action-dispatch entry).
const pinia = createPinia();
setActivePinia(pinia);
const app = createApp(AppShell, { connectionStatus: "ready" });
app.use(pinia);
app.mount(resolveMountPoint());

const store = useElosernStore();
const bridge = createWindowBridge(store);

// Stable test hook (the repository's `__`-prefixed harness-hook convention,
// cf. __elosernWs / __elosernSent): the managed-browser check drives the
// bridge's façade entry points through this handle.
window.__elosernBridge = { store: store, facade: bridge.facade };
