import { h, onBeforeUnmount, onMounted, ref } from "vue";
import HudFrame from "../../components/HudFrame.vue";
import SceneBackdrop from "../../components/SceneBackdrop.vue";
import {
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
  ART_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// SceneBackdrop (H1, webclient-hud-01-shell-and-scene): the truthful scene
// backdrop. Deterministic offline args cover every scene status and both
// stage modes (task 4.4): done / pending-with-prior / pending-without-prior
// / missing / failed / unavailable.

function scenePanel(overrides) {
  return {
    ...ART_PANEL_SAMPLE,
    ...overrides,
  };
}

// The shared fixture names a generated scene under `/art/scenes/`, which
// Storybook does not serve, so the "done" stories would degrade to the
// failed-load fallback. They show a redesign sample painting instead,
// served under `/art/showcase/` (Storybook only), through the same `/art/`
// URL vocabulary the art validator accepts.
const SHOWCASE_SCENE_URL = "/art/showcase/sample-forest.webp";
const DONE = scenePanel({
  scene: { ...ART_PANEL_SAMPLE.scene, url: SHOWCASE_SCENE_URL, label: "北岸大道", alt: "林蔭覆蓋的河岸大道" },
});

const PENDING_WITHOUT_PRIOR = scenePanel({
  scene: {
    ...ART_PANEL_SAMPLE.scene,
    subject_key: null,
    status: "pending",
    url: null,
    aspect_ratio: null,
    placeholder: { kind: "missing", label: "場景圖像尚未生成" },
  },
});

const MISSING = scenePanel({
  scene: {
    ...ART_PANEL_SAMPLE.scene,
    subject_key: null,
    status: "missing",
    url: null,
    aspect_ratio: null,
    placeholder: { kind: "missing", label: "場景圖像尚未生成" },
  },
});

const FAILED = scenePanel({
  scene: {
    ...ART_PANEL_SAMPLE.scene,
    subject_key: null,
    status: "failed",
    url: null,
    aspect_ratio: null,
    placeholder: { kind: "failed", label: "場景圖像生成失敗" },
  },
});

// The stage the backdrop lives on. In the app the backdrop is the lowest
// layer of the HudFrame stage, which fills the viewport under the 48px top
// band, and the shell's rules (app-shell.css) size it to the stage box —
// from the top band's lower edge to the bottom band's upper edge — and
// centre the caption plate between the portraits. A fixed short wrapper
// leaves that box a few pixels tall (the band alone is `--band-h`), so each
// story renders the real stage: a viewport-sized frame (pulled up over the
// preview's top-band padding) holding HudFrame, with the backdrop in its
// `backdrop` slot and the band chrome drawn below it.
function stage(mode, backdrop, frameProps = {}) {
  return h(
    "div",
    { style: "position: relative; height: 100vh; margin-top: calc(-1 * var(--header-h));" },
    [h(HudFrame, { mode, ...frameProps }, { backdrop })],
  );
}

const renderBackdrop = (args) => ({
  render: () => stage(args.mode, () => h(SceneBackdrop, args)),
});

// The next scene is still generating: the panel names it, and the painting
// of the scene before it stays on stage, dimmed, under the pending notice.
const PENDING_AFTER_DONE = {
  ...ART_PANEL_PENDING_SAMPLE,
  scene: { ...ART_PANEL_PENDING_SAMPLE.scene, label: "北岸大道", alt: "林蔭覆蓋的河岸大道" },
};

// The pending-with-prior story seeds the prior image through the exposed
// method, so the dimmed prior image renders with the generating label.
function renderPendingWithPrior() {
  return {
    setup() {
      const backdrop = ref(null);
      onMounted(() => {
        backdrop.value?.setPriorImage(SHOWCASE_SCENE_URL);
      });
      return () =>
        stage("exploration", () =>
          h(SceneBackdrop, { ref: backdrop, art: PENDING_AFTER_DONE, mode: "exploration" }),
        );
    },
  };
}

export default {
  title: "Core/SceneBackdrop",
  component: SceneBackdrop,
  parameters: {
    docs: {
      description: {
        component:
          "The truthful scene backdrop: a done same-origin image cover-cropped " +
          "as the lowest stage layer; a pending scene keeps its prior image " +
          "dimmed with the `目前場景圖片生成中` label; every degraded state renders " +
          "the mode's gradient stage with a truthful placeholder label. The " +
          "scene label and alt render as text outside the bitmap, on the " +
          "one-line caption plate centred on the stage floor. Each story " +
          "renders the backdrop in the real HudFrame stage, so the stage box, " +
          "the band, and the caption sit where they do in the app.",
      },
    },
  },
};

export const DoneExploration = {
  render: renderBackdrop,
  args: { art: DONE, mode: "exploration" },
};

export const DoneCombat = {
  render: renderBackdrop,
  args: { art: DONE, mode: "combat" },
};

export const PendingWithoutPrior = {
  render: renderBackdrop,
  args: { art: PENDING_WITHOUT_PRIOR, mode: "exploration" },
};

export const PendingWithPrior = {
  render: renderPendingWithPrior,
};

export const Missing = {
  render: renderBackdrop,
  args: { art: MISSING, mode: "creation" },
};

export const Failed = {
  render: renderBackdrop,
  args: { art: FAILED, mode: "exploration" },
};

export const Unavailable = {
  render: renderBackdrop,
  args: { art: ART_PANEL_UNAVAILABLE_SAMPLE, mode: "exploration" },
};

// The scene crossfade (webclient-scene-transitions, design D2): every few
// seconds the committed scene changes to another painting. The next image is
// decoded first — until then the current one dims, as a stale scene — and
// then fades in above it while the previous one fades out; the label and
// alternative text switch at once. The paintings are the redesign samples
// Storybook serves under `/art/showcase/`.
const SHOWCASE_SCENES = [
  { url: "/art/showcase/sample-town.webp", label: "石板廣場", alt: "午後陽光下的市集廣場與遠方的鐘樓" },
  { url: "/art/showcase/sample-forest.webp", label: "北岸大道", alt: "林蔭覆蓋的河岸大道" },
  { url: "/art/showcase/sample-guild.webp", label: "西風酒館", alt: "燈火溫暖的酒館大廳" },
];

function renderSceneChange() {
  return {
    setup() {
      const index = ref(0);
      let timer = null;
      onMounted(() => {
        timer = setInterval(() => {
          index.value = (index.value + 1) % SHOWCASE_SCENES.length;
        }, 3000);
      });
      onBeforeUnmount(() => clearInterval(timer));
      return () => {
        const shown = SHOWCASE_SCENES[index.value];
        const art = scenePanel({
          scene: { ...ART_PANEL_SAMPLE.scene, url: shown.url, label: shown.label, alt: shown.alt },
        });
        return stage("exploration", () => h(SceneBackdrop, { art, mode: "exploration" }));
      };
    },
  };
}

export const SceneChange = {
  render: renderSceneChange,
};

// The terminal round hold: exploration mode is committed while beatHold keeps
// combat decoration (gradient, combat sample wash, and veil) active on the stage.
export const TerminalCombatHold = {
  render: () => ({
    render: () =>
      stage(
        "exploration",
        () => h(SceneBackdrop, { art: PENDING_WITHOUT_PRIOR, mode: "combat" }),
        { beatHold: true },
      ),
  }),
};
