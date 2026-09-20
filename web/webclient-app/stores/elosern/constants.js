// The module-level toast constants of the composed Elosern store
// (webclient-action-feedback D1): client-local view state — never persisted,
// never part of the protocol reducer snapshot.
// The bounded lifetime and FIFO cap mirror the redesign draft's queue
// (5200 ms, at most four entries).

export const TOAST_LIFETIME_MS = 5200;
export const TOAST_QUEUE_MAX = 4;
