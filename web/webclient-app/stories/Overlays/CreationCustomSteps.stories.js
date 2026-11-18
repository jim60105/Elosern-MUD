import { h, reactive } from "vue";
import CreationCustomSteps from "../../components/CreationCustomSteps.vue";
import { useCreationOverlay } from "../../composables/use-creation-overlay.js";
import { CREATION_PANEL_CUSTOM_DRAFT_SAMPLE, CREATION_PANEL_SAMPLE } from "../fixtures.js";

// CreationCustomSteps (creation-stepped-form; design §6): the custom form's
// step rail, one step page and previous/next, on its own. The form state is
// the real useCreationOverlay binding set built from the story panel, exactly
// what CreationOverlay hands it, so the story cannot drift from the overlay.
// Confirmation lives in the overlay footer and is not part of this frame.
const frame = (args) => ({
  setup() {
    const props = reactive({ creation: args.creation, open: true, result: null, stage: null, dispatch: null, dispatchState: null, pushToast: null });
    const form = useCreationOverlay(props, () => {});
    if (args.step) form.goToStep(args.step);
    return () =>
      h(
        "div",
        {
          class: "elosern",
          style:
            "position:absolute;inset:0;display:flex;flex-direction:column;padding:16px 32px;box-sizing:border-box;background:var(--ink-950)",
        },
        [h(CreationCustomSteps, { form })],
      );
  },
});

export default {
  title: "Overlays/CreationCustomSteps",
  component: CreationCustomSteps,
  render: frame,
};

// 01 身分 from a saved custom draft.
export const Identity = {
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE, step: "identity" },
};

// 02 角色故事.
export const Story = {
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE, step: "story" },
};

// 03 能力配置: two columns of axes; the rail shows the remaining points.
export const Allocation = {
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE, step: "allocation" },
};

// A fresh form: every field at its default, the full budget remaining.
export const FreshForm = {
  args: { creation: CREATION_PANEL_SAMPLE, step: "identity" },
};
