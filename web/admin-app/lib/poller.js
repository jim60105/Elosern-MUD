// Visibility-aware polling (gm-portal-s2b-dashboard, design D6).
//
// One chained setTimeout (never setInterval, so a slow response cannot stack
// requests): the next poll is scheduled only after the current one settles.
// While the document is hidden nothing is scheduled; becoming visible again
// cancels any pending timer and polls immediately. A manual refresh during a
// flight is coalesced into the flight already running. Every load carries a
// sequence number and only the newest settled load may publish, so a stale
// response can never replace a newer snapshot. After `stop()` nothing
// publishes at all. A failed load keeps the last good data (the caller shows
// it as stale); an authorization failure stops polling so the router guard
// can take over without a loop.

export const POLL_INTERVAL_MS = 5000;
const STOPPING_CODES = new Set(["unauthenticated", "forbidden"]);

export function createPoller({
  load,
  onData = () => {},
  onError = () => {},
  intervalMs = POLL_INTERVAL_MS,
  doc = globalThis.document,
  timers = globalThis,
} = {}) {
  let timer = null;
  let running = false;
  let flight = null;
  let sequence = 0;
  let published = 0;

  const hidden = () => doc?.visibilityState === "hidden";

  function clearTimer() {
    if (timer !== null) {
      timers.clearTimeout(timer);
      timer = null;
    }
  }

  function schedule() {
    clearTimer();
    if (!running || hidden()) return;
    timer = timers.setTimeout(() => {
      timer = null;
      refresh();
    }, intervalMs);
  }

  function refresh() {
    if (!running) return Promise.resolve();
    if (flight) return flight;
    clearTimer();
    const token = ++sequence;
    flight = Promise.resolve()
      .then(() => load())
      .then(
        (data) => {
          if (running && token > published) {
            published = token;
            onData(data);
          }
        },
        (error) => {
          if (!running || token < published) return;
          onError(error);
          if (STOPPING_CODES.has(error?.code)) stop();
        },
      )
      .finally(() => {
        flight = null;
        schedule();
      });
    return flight;
  }

  function onVisibility() {
    if (!running) return;
    if (hidden()) {
      clearTimer();
    } else {
      refresh();
    }
  }

  function start() {
    if (running) return;
    running = true;
    doc?.addEventListener?.("visibilitychange", onVisibility);
    if (!hidden()) refresh();
  }

  function stop() {
    running = false;
    clearTimer();
    doc?.removeEventListener?.("visibilitychange", onVisibility);
  }

  return {
    start,
    stop,
    refresh,
    get running() {
      return running;
    },
    get pending() {
      return flight !== null;
    },
  };
}
