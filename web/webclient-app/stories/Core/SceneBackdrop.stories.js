import { h, onBeforeUnmount, onMounted, ref } from "vue";
import HudFrame from "../../components/HudFrame.vue";
import SceneBackdrop from "../../components/SceneBackdrop.vue";
import {
  ART_PANEL_FAILED_SAMPLE,
  ART_PANEL_MALFORMED_SAMPLE,
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
  ART_PANEL_UNAVAILABLE_SAMPLE,
  SCENE_SUBJECT,
  fixtureDigest,
  sceneBlock,
  sceneBundledResource,
  sceneDescriptor,
  sceneResource,
} from "../fixtures.js";

// SceneBackdrop (H1, webclient-hud-01-shell-and-scene; change
// unified-scene-rendering): the truthful scene backdrop. Deterministic offline
// args cover every committed state and both stage modes: a done descriptor, a
// pending regeneration with and without retained content, a missing
// generation, a failed regeneration, a malformed room and the panel's
// unavailable form.

function scenePanel(overrides) {
  return {
    ...ART_PANEL_SAMPLE,
    ...overrides,
  };
}

// The completed bundled illustrations Storybook serves from `web/static`
// under `/art/scenes/` (see `.storybook/main.js`): the generated-candidate
// story shows a real painting through the same `/art/` URL vocabulary every
// surface uses.
const SHOWCASE_SCENE_URL = "/art/scenes/forest_path.webp";

// One scene descriptor whose generated candidate paints `url`: the same shape
// the server emits, with the required bundled illustration behind it.
function doneScene(url, label, alt) {
  return sceneBlock(
    { label, alt },
    sceneDescriptor({
      revision: fixtureDigest(`scene-revision-${label}`),
      attempts: [
        {
          type: "image",
          source_id: `scene.generated:${SCENE_SUBJECT}`,
          rank: 20,
          resource: sceneResource({
            version: fixtureDigest(`scene-${label}`),
            url,
          }),
        },
        {
          type: "image",
          source_id: "scene.bundled:river_dawn",
          rank: 40,
          resource: sceneBundledResource("river_dawn"),
        },
      ],
    }),
  );
}

const DONE = scenePanel({
  scene: doneScene(SHOWCASE_SCENE_URL, "北岸大道", "林蔭覆蓋的河岸大道"),
});

// A generation that has not produced anything yet and that this browser never
// showed a prior image for: the descriptor still authorizes the retained
// generated source, but nothing is retained, so the status badge states the
// factual absence.
const PENDING_WITHOUT_PRIOR = scenePanel({
  scene: {
    ...ART_PANEL_PENDING_SAMPLE.scene,
    label: "北岸大道",
    alt: "林蔭覆蓋的河岸大道",
  },
});

// A scene whose recorded generation is missing entirely (no job, no output):
// the required bundled illustration is the current attempt.
const MISSING = scenePanel({
  scene: sceneBlock(
    { label: "北岸大道", alt: "林蔭覆蓋的河岸大道" },
    sceneDescriptor({
      generation_state: "missing",
      revision: fixtureDigest("scene-revision-missing"),
      attempts: [
        {
          type: "image",
          source_id: "scene.bundled:river_dawn",
          rank: 40,
          resource: sceneBundledResource("river_dawn"),
        },
      ],
    }),
  ),
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

// The next scene is still generating: the panel names it, and the good image
// of the scene before it stays on stage under the pending notice.
const PENDING_AFTER_DONE = {
  ...ART_PANEL_PENDING_SAMPLE,
  scene: { ...ART_PANEL_PENDING_SAMPLE.scene, label: "北岸大道", alt: "林蔭覆蓋的河岸大道" },
};

// The pending-with-prior story seeds the retained content through the exposed
// method (which carries the descriptor's own retention authorization), so the
// retained image renders with the factual progress notice.
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

export const FailedRegeneration = {
  render: renderBackdrop,
  args: { art: ART_PANEL_FAILED_SAMPLE, mode: "exploration" },
};

export const MalformedMetadata = {
  render: renderBackdrop,
  args: { art: ART_PANEL_MALFORMED_SAMPLE, mode: "exploration" },
};

export const Unavailable = {
  render: renderBackdrop,
  args: { art: ART_PANEL_UNAVAILABLE_SAMPLE, mode: "exploration" },
};

// The scene crossfade (webclient-scene-transitions, design D2): every few
// seconds the same logical place commits a new painting. The current image
// stays on screen until the replacement's pixels are observed, then the two
// crossfade and the label and alternative text switch at once. The paintings
// are committed bundled illustrations, so no story fetches invented media.
const SHOWCASE_SCENES = [
  { url: "/art/scenes/city_street.webp", label: "石板廣場", alt: "午後陽光下的市集廣場與遠方的鐘樓" },
  { url: "/art/scenes/forest_path.webp", label: "北岸大道", alt: "林蔭覆蓋的河岸大道" },
  { url: "/art/scenes/tavern_interior.webp", label: "西風酒館", alt: "燈火溫暖的酒館大廳" },
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
          scene: doneScene(shown.url, shown.label, shown.alt),
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
// combat decoration (gradient and veil) active on the stage.
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
