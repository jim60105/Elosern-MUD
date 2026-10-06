import { h } from "vue";
import "../web/webclient-app/styles/tokens.css";
import "../web/webclient-app/styles/fonts.css";
import "../web/webclient-app/styles/fonts-mono.css";
import "../web/webclient-app/styles/app-shell.css";
import "../web/static/webclient/css/ansi_palette.css";
import "../web/admin-app/styles/gm.css";
import { installUiScale } from "../web/webclient-app/lib/ui_scale.js";

// The live client's chrome factor, so a story viewed above 790px height
// renders at the same proportional scale (webclient-proportional-ui-scale).
// The GM portal never installs it (its tokens resolve at --ui-scale 1), so a
// GM story releases the scaler and a game story re-installs it; a docs page
// only ever renders stories of one title, so the two never share a frame.
let disposeUiScale = installUiScale();

function syncUiScale(isGmStory) {
  if (isGmStory && disposeUiScale) {
    disposeUiScale();
    disposeUiScale = null;
  } else if (!isGmStory && !disposeUiScale) {
    disposeUiScale = installUiScale();
  }
}

export const decorators = [
  (story, context) => {
    const isGmStory = context.title.startsWith("GM/");
    syncUiScale(isGmStory);
    if (isGmStory) {
      return {
        render: () => h("div", { class: "gm-root", style: { minHeight: "100vh" } }, [h(story())]),
      };
    }
    return gameStory(story, context);
  },
];

function gameStory(story, context) {
  return {
    render: () => context.title === "Core/AppShell"
      ? h(story())
      : h("div", {
        class: "elosern elosern-root",
        style: { paddingTop: "var(--header-h)", boxSizing: "border-box", overflow: "auto" },
      }, [h(story())]),
  };
}

export const initialGlobals = {
  backgrounds: { value: "ink-950" },
};

export const parameters = {
  layout: "fullscreen",
  backgrounds: {
    options: { "ink-950": { name: "ink-950", value: "#0b0d10" } },
  },
};
