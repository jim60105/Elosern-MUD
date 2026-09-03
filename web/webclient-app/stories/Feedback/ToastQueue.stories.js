import { h, ref } from "vue";
import ToastQueue from "../../components/ToastQueue.vue";

// ToastQueue (action-feedback family): the client-local action-feedback toast
// queue (webclient-action-feedback). A passive renderer over the store's
// bounded FIFO queue — title with the draft's leading icon, optional subtitle,
// seal-red left edge for the `crit` tone, click-to-dismiss. The showcase stays
// truthful: the entries below are client-composed display fixtures, exactly
// the shape `pushToast` accepts; no backend read model is presented or mocked.

const renderQueue = (args) => ({ render: () => h(ToastQueue, args) });

export default {
  title: "Feedback/ToastQueue",
  component: ToastQueue,
};

export const InfoToast = {
  render: renderQueue,
  args: {
    toasts: [{ id: 1, title: "概念提案已套用到自訂表單", tone: "info" }],
  },
};

export const CritToast = {
  render: renderQueue,
  args: {
    toasts: [{ id: 1, title: "概念服務目前無法使用，請稍後再試。", tone: "crit" }],
  },
};

export const WithSubtitle = {
  render: renderQueue,
  args: {
    toasts: [{ id: 1, title: "概念提案已套用到自訂表單", sub: "貓人見習者", tone: "info" }],
  },
};

// The queue cap: at most four entries are alive at once (FIFO eviction).
export const FullQueue = {
  render: renderQueue,
  args: {
    toasts: [
      { id: 1, title: "已進入霧骨渡口", tone: "info" },
      { id: 2, title: "概念服務目前無法使用，請稍後再試。", tone: "crit" },
      { id: 3, title: "已離開商店", tone: "info" },
      { id: 4, title: "動作未生效，請重試或返回上層。", tone: "crit" },
    ],
  },
};

// The empty state: the queue is always mounted and renders nothing when idle.
export const Empty = {
  render: renderQueue,
  args: { toasts: [] },
};

// The close interaction: the entry's click-to-dismiss contract, reviewable in
// the showcase. The local list below is DEMO WIRING ONLY — the production
// queue lives in the store (webclient-action-feedback D1); this copy just
// mirrors AppClient's `@dismiss` binding so the emitted dismiss visibly
// removes the clicked entry. The play contract is observable: a drift in the
// entry testid, the click handler, or the dismiss emit FAILS the story.
export const DismissOnClick = {
  render: (args) => ({
    setup() {
      const toasts = ref(args.toasts.map((toast) => ({ ...toast })));
      const dismiss = (id) => {
        const index = toasts.value.findIndex((toast) => toast.id === id);
        if (index !== -1) {
          toasts.value.splice(index, 1);
        }
      };
      return () => h(ToastQueue, { toasts: toasts.value, onDismiss: dismiss });
    },
  }),
  args: {
    toasts: [
      { id: 1, title: "概念提案已套用到自訂表單", sub: "貓人見習者", tone: "info" },
      { id: 2, title: "概念服務目前無法使用，請稍後再試。", tone: "crit" },
    ],
  },
  play: async ({ canvasElement }) => {
    const first = canvasElement.querySelector('[data-testid="feedback-toast-1"]');
    if (!first) {
      throw new Error("DismissOnClick: the first fixture entry did not render");
    }
    first.click();
    let gone = !canvasElement.querySelector('[data-testid="feedback-toast-1"]');
    for (let tick = 0; tick < 100 && !gone; tick += 1) {
      await new Promise((resolve) => setTimeout(resolve, 20));
      gone = !canvasElement.querySelector('[data-testid="feedback-toast-1"]');
    }
    if (!gone) {
      throw new Error("DismissOnClick: clicking an entry did not dismiss it");
    }
    // The other entry is untouched (dismissing one never clears the queue).
    if (!canvasElement.querySelector('[data-testid="feedback-toast-2"]')) {
      throw new Error("DismissOnClick: dismissing one entry removed another");
    }
  },
};
