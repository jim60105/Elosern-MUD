// The shop window's trade seam (webclient-shop-window): one `shop.buy` /
// `shop.sell` through the single dispatch entry, the request it made, and
// that request's committed non-success result ({ code, message }) — for
// example the ordinary `insufficient_funds` refusal — so the window can state it
// in its action bar while the modal covers the narrative. The narrative line
// is unchanged; nothing here is retried. Like use-rest-wait.js, the request
// is forgotten on an epoch or generation change.
import { computed, ref, watch } from "vue";
import { NON_SUCCESS_OUTCOMES } from "../stores/elosern/shared.js";

const TRADE_ACTIONS = new Set(["shop.buy", "shop.sell"]);

export function useShopTrade(store, { dispatchIntent }) {
  const request = ref(null);
  // The request whose stated result the window dismissed (it stays tracked
  // for `tradePending`).
  const dismissed = ref(null);
  watch([() => store.view.epoch, () => store.view.generation], () => {
    request.value = null;
    dismissed.value = null;
  });

  const tradeNotice = computed(() => {
    const result = store.view.lastActionResult;
    if (request.value === null || dismissed.value === request.value || result?.requestId !== request.value) return null;
    if (NON_SUCCESS_OUTCOMES.indexOf(result.outcome) === -1) return null;
    const message = typeof result.message === "string" && result.message.trim() !== "" ? result.message : null;
    return message ? { code: result.code ?? null, message } : null;
  });

  const tradePending = computed(
    () => request.value !== null && store.view.dispatch?.inFlight?.requestId === request.value,
  );

  function onShopTrade(intent) {
    if (!intent || !TRADE_ACTIONS.has(intent.action_id)) return null;
    const requestId = dispatchIntent(intent.action_id, intent.payload);
    request.value = requestId;
    return requestId;
  }

  // The window drops a stated result when its member, tab or row changes.
  function clearTradeNotice() {
    dismissed.value = request.value;
  }

  return { tradeNotice, tradePending, onShopTrade, clearTradeNotice };
}
