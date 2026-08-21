// Retires the stock and pre-JS text fallback that the mounted Vue app
// replaces (the webclient-vue-application mount retires the replaced text
// fallback scenario): the fallback is hidden, never removed, so the degraded
// text path stays in the DOM to be re-activated later (C3) while the mounted
// application cannot stack with it in document flow and get pushed below the
// visible viewport. Idempotent; safe to call from the shell mount and again
// after the D10 text console has attached.
const RETIRED_MARKER = "app-mount";

function retire(el) {
  if (!el || el.hasAttribute("data-elosern-retired")) {
    return false;
  }
  el.style.display = "none";
  el.setAttribute("data-elosern-retired", RETIRED_MARKER);
  return true;
}

export function retireReplacedFallback(doc) {
  const document = doc || (typeof globalThis !== "undefined" ? globalThis.document : undefined);
  if (!document || typeof document.querySelectorAll !== "function") {
    return [];
  }
  const retired = [];
  for (const selector of ["#messagewindow", '[data-testid="text-console"]']) {
    for (const el of Array.from(document.querySelectorAll(selector))) {
      if (retire(el)) {
        retired.push(el);
      }
    }
  }
  return retired;
}
