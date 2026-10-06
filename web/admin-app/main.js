// GM portal entry (gm-portal-s1-foundation). The ONLY game-tree imports
// allowed anywhere in web/admin-app are the shared design tokens and font
// faces below (enforced by scripts/gm-import-boundary.mjs).
import "@elosern/styles/tokens.css";
import "@elosern/styles/fonts.css";
import "@elosern/styles/fonts-mono.css";
import "./styles/page.css";
import "./styles/gm.css";

import { createApp, reactive } from "vue";
import App from "./App.vue";
import { createGmApi } from "./lib/api.js";
import { createSessionState } from "./lib/session.js";
import { createGmRouter } from "./router.js";

const mount = document.getElementById("gm-app");
const config = Object.freeze({
  loginUrl: mount.dataset.loginUrl || "/auth/login/",
  logoutUrl: mount.dataset.logoutUrl || "",
});

const authState = reactive({ forbidden: false });
const router = createGmRouter({ authState });
const api = createGmApi({
  loginUrl: config.loginUrl,
  onForbidden() {
    authState.forbidden = true;
    if (router.currentRoute.value.name !== "forbidden") router.replace({ name: "forbidden" });
  },
});
const session = createSessionState(api);

createApp(App)
  .provide("gmConfig", config)
  .provide("gmApi", api)
  .provide("gmSession", session)
  .use(router)
  .mount(mount);
