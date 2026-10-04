import { h, reactive } from "vue";
import LettersPanel from "../../components/LettersPanel.vue";

export default { title: "World/LettersPanel", component: LettersPanel };
// Synthetic result-channel fixture; opening the folio never opens its letter.
const render = (args) => ({
  setup() {
    let sequence = 0;
    const page = { branch: args.branch, letters: [{ source_id: "synthetic-letter", sender_id: "12", sent_tick: 17, read_tick: null }], next: null };
    const store = {
      view: reactive({ epoch: "synthetic", generation: 1, connected: true, dispatch: { inFlight: null }, lastActionResult: null }),
      dispatchAction(action, payload) {
        const id = `synthetic-${++sequence}`;
        queueMicrotask(() => {
          store.view.lastActionResult = {
            requestId: id, epoch: "synthetic", outcome: "success",
            data: action === "letters.read" ? { source_id: payload.source_id, sender_id: "12", body_parts: ["旅人：\n\n你離開後，村口的樹已長出新葉。若再經過，請來共食棚坐一會兒。\n\n願路途平安。"] } : { ...page, count: 0 },
          };
        });
        return id;
      },
    };
    return () => h(LettersPanel, { store });
  },
});
export const Portable = { render, args: { branch: false } };
export const Branch = { render, args: { branch: true } };
