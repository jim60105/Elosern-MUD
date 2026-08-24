import { h, onMounted, ref } from "vue";
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

const renderBackdrop = (args) => ({
  render: () => h("div", { style: "position: relative; width: 100%; height: 320px; overflow: hidden;" }, [
    h(SceneBackdrop, args),
  ]),
});

// The pending-with-prior story seeds the prior image through the exposed
// method, so the dimmed prior image renders with the generating label.
function renderPendingWithPrior() {
  return {
    setup() {
      const backdrop = ref(null);
      onMounted(() => {
        backdrop.value?.setPriorImage(ART_PANEL_SAMPLE.scene.url);
      });
      return {
        backdrop,
        render: () =>
          h("div", { style: "position: relative; width: 100%; height: 320px; overflow: hidden;" }, [
            h(SceneBackdrop, { ref: "backdrop", art: ART_PANEL_PENDING_SAMPLE, mode: "exploration" }),
          ])
      };
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
          "scene label and alt render as text outside the bitmap.",
      },
    },
  },
};

export const DoneExploration = {
  render: renderBackdrop,
  args: { art: ART_PANEL_SAMPLE, mode: "exploration" },
};

export const DoneCombat = {
  render: renderBackdrop,
  args: { art: ART_PANEL_SAMPLE, mode: "combat" },
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
