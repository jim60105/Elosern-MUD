// The room-actions group of the composed Elosern store (exploration-room-
// actions design D1/D3/D4/D5): the place card's 查看房間, and the client-local
// room card slice — the wait card the place card's 等待 opens and the
// suggestions card the 建議 pill opens.
//
// A room card is client-local state, never a router frame: opening it sends
// no request and pushes nothing. It is its own slice beside the presence
// card (`ctx.presenceCard`), so the presence rail's consumers (the person
// focus, the departure check, the speaker line) never see a room card; the
// two share one "a centred card is open" predicate (`ctx.centredCardOpen`)
// that hides the rail, stops the compass, and claims the digits. Opening one
// kind of card closes the other: the `choices` anchor holds one card.
//
// Every row is re-resolved from the committed panels at activation time and
// submitted through the one gated exploration activation
// (`activateExplorationRow`), so payloads, the command echo, and the
// in-flight and awaiting-revision lock are the retired router rows'.

// The committed location (room identity plus the committed current node), as
// the presence card records it: a move closes an open room card.
function locationOf(rs, currentNode) {
  const panel = (rs && rs.panels && rs.panels.exploration) || null;
  if (!panel || panel.available === false) {
    return null;
  }
  const room = (panel.look && panel.look.room) || null;
  if (!room || room.identity === undefined || room.identity === null) {
    return null;
  }
  return { room: String(room.identity), node: currentNode == null || currentNode === "" ? null : String(currentNode) };
}

function isMove(from, to) {
  if (!from || !to) {
    return false;
  }
  if (from.room !== to.room) {
    return true;
  }
  return from.node !== null && to.node !== null && from.node !== to.node;
}

const ROOM_CARD_KINDS = new Set(["wait", "suggestions"]);

export function applyRoomActions(ctx) {
  // null | {kind: "wait" | "suggestions", location}
  ctx.roomCard = null;

  function currentLocation(rs) {
    return locationOf(rs, ctx.frameResolver.explorationExits().currentNode);
  }

  // One centred card at a time: a presence card or a room card.
  ctx.centredCardOpen = function centredCardOpen() {
    return ctx.presenceCard !== null || ctx.roomCard !== null;
  };

  // The place card's 查看房間 (design D3): the committed room's look row,
  // through the gate. Nothing is submitted while locked.
  ctx.activateRoomLook = function activateRoomLook() {
    const rs = ctx.reducer.getState();
    if (rs.mode !== "exploration") {
      return { sent: false, handled: false, reason: "mode" };
    }
    return ctx.activateExplorationRow(ctx.frameResolver.explorationRoomLook());
  };

  // Open the wait card or the suggestions card. Local: no request, no frame.
  // The suggestions card opens only while the committed envelope presents
  // one (its status is not `unavailable`).
  ctx.openRoomCard = function openRoomCard(kind) {
    const rs = ctx.reducer.getState();
    if (!ROOM_CARD_KINDS.has(kind) || rs.mode !== "exploration") {
      return false;
    }
    const source = kind === "wait" ? ctx.frameResolver.explorationWait() : ctx.frameResolver.explorationSuggestions();
    if (!source || (kind === "suggestions" && ctx.activeSubDock.value)) {
      return false;
    }
    ctx.presenceCard = null;
    ctx.roomCard = { kind, location: currentLocation(rs) };
    ctx.publishView();
    return true;
  };

  ctx.closeRoomCard = function closeRoomCard() {
    if (ctx.roomCard === null) {
      return false;
    }
    ctx.roomCard = null;
    ctx.publishView();
    return true;
  };

  // A wait row (design D5), re-resolved now. `dream` adds the dream flag to
  // the sleep row's payload: the 進入夢境協作？ question's 是 (the server can
  // only enter the dream as part of the same sleep request). The rest row
  // opens the form in the view and is never submitted here.
  ctx.activateWaitRow = function activateWaitRow(key, options = {}) {
    if (!ctx.roomCard || ctx.roomCard.kind !== "wait") {
      return { sent: false, handled: false, reason: "missing" };
    }
    const rows = ctx.frameResolver.explorationWait();
    const found = rows ? rows.find((item) => item.key === key) : null;
    if (!found || !found.actionId) {
      return { sent: false, handled: false, reason: "missing" };
    }
    const row =
      key === "wait-sleep" && options.dream === true
        ? { ...found, payload: { ...(found.payload || {}), dream: true } }
        : found;
    const outcome = ctx.activateExplorationRow(row);
    // A card row's action takes the surface over, so the card closes with its
    // dispatch; the dismiss row keeps the card exactly as last committed —
    // the committed `unavailable` envelope closes it (`settleRoomCard`), so a
    // stale/busy rejection never tears down a surface the commit still backs
    // (webclient-context-actions-suggestions' preserved dismiss invariant).
    if (outcome.sent && row.actionId !== "options.dismiss") {
      ctx.closeRoomCard();
    }
    return outcome;
  };

  // A suggestions card row (design D4): a card or the dismiss row, matched by
  // its builder key in the envelope committed right now.
  ctx.activateSuggestion = function activateSuggestion(key) {
    if (!ctx.roomCard || ctx.roomCard.kind !== "suggestions") {
      return { sent: false, handled: false, reason: "missing" };
    }
    const content = ctx.frameResolver.explorationSuggestions();
    const row = content ? content.items.find((item) => item.key === key) : null;
    if (!row || !row.actionId) {
      return { sent: false, handled: false, reason: "missing" };
    }
    const outcome = ctx.activateExplorationRow(row);
    if (outcome.sent) {
      ctx.closeRoomCard();
    }
    return outcome;
  };

  // The commit-time settle, run at every publish: a mode other than
  // exploration, a committed move, or an unavailable exploration panel
  // closes the card; the suggestions card also closes once the committed
  // envelope no longer presents one (`unavailable`, withdrawn, or a
  // transport reset's empty panels) and while a re-homed sub-dock owns the
  // surface (the options-surface rule the 建議 pill follows too).
  ctx.settleRoomCard = function settleRoomCard(rs) {
    const card = ctx.roomCard;
    if (card === null) {
      return;
    }
    if (rs.mode !== "exploration") {
      ctx.roomCard = null;
      return;
    }
    const location = currentLocation(rs);
    if (location === null || isMove(card.location, location)) {
      ctx.roomCard = null;
      return;
    }
    card.location = { room: location.room, node: location.node ?? (card.location ? card.location.node : null) };
    if (card.kind === "suggestions" && (!ctx.frameResolver.explorationSuggestions() || ctx.activeSubDock.value)) {
      ctx.roomCard = null;
    }
  };

  // Drop the slice without publishing (a root reset or a new transport).
  ctx.resetRoomCard = function resetRoomCard() {
    ctx.roomCard = null;
  };

  // The view slice: the open card, the place card's room row, the wait rows,
  // and the suggestions content (null while the envelope presents nothing).
  ctx.roomActionsView = function roomActionsView() {
    return {
      roomCard: ctx.roomCard ? { kind: ctx.roomCard.kind } : null,
      roomLook: ctx.frameResolver.explorationRoomLook(),
      waitRows: ctx.frameResolver.explorationWait(),
      suggestionsCard: ctx.frameResolver.explorationSuggestions(),
    };
  };
}
