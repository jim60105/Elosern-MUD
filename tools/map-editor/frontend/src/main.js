// Standalone map editor entry. The ONLY game-tree imports anywhere in this
// frontend are the design tokens, the font faces and the pure ui-scale
// function below (enforced by scripts/import-boundary.mjs); the game shell
// stylesheet, stores, components and transport are never imported.
import "@game/tokens.css";
import "@game/fonts.css";
import "@game/fonts-mono.css";
import "./styles/editor.css";

import { createApp } from "vue";
import { installUiScale } from "@game/ui_scale.js";
import App from "./App.vue";

installUiScale();
createApp(App).mount("#map-editor");
