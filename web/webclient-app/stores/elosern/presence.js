// The presence group of the composed Elosern store (exploration-presence-rail
// design D2/D5/D7): the presence rail's entries, the client-local card slice
// (the person-focus verb card and the overflow card), the one gated
// activation every exploration row outside the router goes through, the
// rail's digit picks, and the commit-time card settle.
//
// The card is client-local state, never a router frame: opening it sends no
// request and pushes nothing. It lives here (not in a component) so the
// store's digit path can open it, can tell whether one is open, and so a
// departed person or a committed move closes it in the commit that publishes
// that change.

import { RAIL_MAX, RAIL_MORE_KEY, railOverflow, railSlots } from "../../components/presence-rail.js";

// The committed location: the room identity plus the committed current node
// (wilderness rooms are reused across coordinates). Null while the
// exploration panel is absent or unavailable, which never counts as a move.
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

// A move: the room identity changed, or both current nodes are known and
// differ. A node that merely appears or disappears (the local map becoming
// available or unavailable in the same room) is not a move.
function isMove(from, to) {
  if (!from || !to) {
    return false;
  }
  if (from.room !== to.room) {
    return true;
  }
  return from.node !== null && to.node !== null && from.node !== to.node;
}

export function applyPresence(ctx) {
  // null | {kind: "verbs", identity, name, openerKey, location}
  //      | {kind: "overflow", openerKey, location}
  ctx.presenceCard = null;
  // The readout's departed flash: null | {seq, name}.
  ctx.presenceNotice = null;
  ctx.presenceNoticeSeq = 0;

  function currentLocation(rs) {
    return locationOf(rs, ctx.frameResolver.explorationExits().currentNode);
  }

  // The committed entries, or null when the panel is unavailable.
  ctx.presenceEntries = function presenceEntries() {
    return ctx.frameResolver.explorationPresence();
  };

  // The one gated activation for an `ExplorationMenu` builder row that lives
  // outside the router (exploration-exit-compass D2, generalized by
  // exploration-presence-rail D2): the exit compass's exits, the rail's look
  // entries, and the verb card's rows. It runs the gate `focusConfirm` runs —
  // the exploration form, the server-authored `enabled` flag, the in-flight
  // and awaiting-revision lock — and hands the row to the one exploration
  // submit handler, so payloads, the command echo, the connection lock in
  // `dispatchAction`, and the local opens (a drawer, the persona editor) are
  // exactly the router path's. The caller passes a row it re-resolved from
  // the committed panels at THIS moment.
  ctx.activateExplorationRow = function activateExplorationRow(item) {
    const rs = ctx.reducer.getState();
    if (!ctx.dockOnExplorationForm(rs)) {
      return { sent: false, handled: false, reason: "mode" };
    }
    if (!item) {
      return { sent: false, handled: false, reason: "missing" };
    }
    if (item.enabled === false) {
      return { sent: false, handled: false, reason: "disabled", item };
    }
    if (ctx.explorationSubmitLocked()) {
      return { sent: false, handled: false, reason: "locked" };
    }
    const before = ctx.lastSubmittedRequestId;
    const handled = ctx.handleExplorationItem(item);
    if (ctx.lastSubmittedRequestId !== before) {
      return { sent: true, handled: true, requestId: ctx.lastSubmittedRequestId };
    }
    // A local open (a drawer, the persona editor) handles the row without a
    // request; an action the dispatch gate refused handles nothing. The row
    // shape decides which: every local-open row of the builders carries no
    // `actionId`, and every row that carries one is a submission.
    return { sent: false, handled: !!handled && !item.actionId, reason: item.actionId ? "refused" : "local" };
  };

  ctx.closePresenceCard = function closePresenceCard() {
    if (ctx.presenceCard === null) {
      return false;
    }
    ctx.presenceCard = null;
    ctx.publishView();
    return true;
  };

  // A rail slot's activation (§4.1): an interact target opens its verb card,
  // `＋N` opens the overflow card, and a bystander or an object submits its
  // look row. The overflow card's picks come back through here, so there is
  // one activation path.
  ctx.activatePresence = function activatePresence(key) {
    const rs = ctx.reducer.getState();
    if (rs.mode !== "exploration") {
      return { sent: false, handled: false, reason: "mode" };
    }
    const entries = ctx.presenceEntries();
    if (!entries) {
      return { sent: false, handled: false, reason: "unavailable" };
    }
    const fromOverflow = ctx.presenceCard !== null && ctx.presenceCard.kind === "overflow";
    const location = currentLocation(rs);
    if (key === RAIL_MORE_KEY) {
      if (entries.length <= RAIL_MAX) {
        return { sent: false, handled: false, reason: "missing" };
      }
      ctx.roomCard = null;
      ctx.presenceCard = { kind: "overflow", openerKey: RAIL_MORE_KEY, location };
      ctx.publishView();
      return { sent: false, handled: true, reason: "local" };
    }
    const entry = entries.find((candidate) => candidate.key === key);
    if (!entry) {
      return { sent: false, handled: false, reason: "missing" };
    }
    if (entry.presence === "target") {
      ctx.roomCard = null;
      ctx.presenceCard = {
        kind: "verbs",
        identity: entry.identity,
        name: entry.label,
        // A person picked on the overflow card returns to its `＋N` slot.
        openerKey: fromOverflow ? RAIL_MORE_KEY : entry.key,
        location,
      };
      ctx.publishView();
      return { sent: false, handled: true, reason: "local" };
    }
    const outcome = ctx.activateExplorationRow(entry);
    if (outcome.sent && fromOverflow) {
      ctx.presenceCard = null;
      ctx.publishView();
    }
    return outcome;
  };

  // A verb card row (§4.3): the focused target's `verbMenuFor` rows,
  // re-resolved now. 查看 closes the card once it is sent; the back row closes
  // it; a row that vanished does nothing.
  ctx.activatePresenceVerb = function activatePresenceVerb(key) {
    const card = ctx.presenceCard;
    if (!card || card.kind !== "verbs") {
      return { sent: false, handled: false, reason: "missing" };
    }
    if (key === "back") {
      ctx.closePresenceCard();
      return { sent: false, handled: true, reason: "local" };
    }
    const menu = ctx.frameResolver.explorationVerbs(card.identity);
    const row = menu && Array.isArray(menu.items) ? menu.items.find((item) => item.key === key && !item.goBack) : null;
    if (!row) {
      return { sent: false, handled: false, reason: "missing" };
    }
    const outcome = ctx.activateExplorationRow(row);
    if (outcome.sent && row.key === "look-target") {
      ctx.closePresenceCard();
    }
    return outcome;
  };

  // The rows a card lists, in its order (the trailing back row excluded):
  // the digits address them.
  function cardPickKeys() {
    const card = ctx.presenceCard;
    if (!card) {
      return [];
    }
    if (card.kind === "verbs") {
      const menu = ctx.frameResolver.explorationVerbs(card.identity);
      return ((menu && menu.items) || []).filter((item) => !item.goBack).map((item) => item.key);
    }
    return railOverflow(ctx.presenceEntries() || []).map((entry) => entry.key);
  }

  // Whether the rail is on the stage: exploration with an available panel
  // that lists someone or something, no card open (a presence card or a room
  // card, exploration-room-actions), and nothing covering the
  // stage (a held combat round, a degraded root, a drawer, an overlay). The
  // digit path and the rail's own render share this one predicate.
  ctx.railVisible = function railVisible(rs) {
    if (!rs || rs.mode !== "exploration" || ctx.centredCardOpen()) {
      return false;
    }
    if (ctx.beatHoldView() || ctx.hudDrawer.value || ctx.hudOverlay.value) {
      return false;
    }
    if (ctx.router.depth() > 0 && ctx.router.degradedRoot()) {
      return false;
    }
    const entries = ctx.presenceEntries();
    return !!entries && entries.length > 0;
  };

  // The rail's digit picks (design D5): `null` when the press is not the
  // rail's (the router path decides), else whether it was claimed. The
  // exploration root is an empty router menu (exploration-room-actions), so
  // no digit falls through to a dock row. While a card is open its rows own
  // the digits; the card's keydown handles them first, and this covers a
  // digit that reaches the store with focus elsewhere. With the rail on the
  // stage every digit is claimed — one beyond the slots does nothing — and
  // with no rail no digit is claimed.
  ctx.presenceDigit = function presenceDigit(key, repeat) {
    const rs = ctx.reducer.getState();
    if (rs.mode !== "exploration" || ctx.router.depth() === 0) {
      return null;
    }
    const slot = Number(key) - 1;
    // An open card owns the digits whatever frame the dock shows, except
    // under a drawer or an overlay (the card stays open beneath a drawer its
    // navigate row opened): those digits are not the card's and not claimed.
    if (ctx.roomCard !== null) {
      // A room card's digits are its own keydown's: the sleep row opens the
      // view's dream question and the rest row the view's form, which the
      // store cannot. A stray digit is claimed and does nothing, so it never
      // reaches the rail beneath the card.
      return !(ctx.hudDrawer.value || ctx.hudOverlay.value);
    }
    if (ctx.presenceCard !== null) {
      if (ctx.hudDrawer.value || ctx.hudOverlay.value) {
        return false;
      }
      if (!repeat) {
        const keys = cardPickKeys();
        if (slot < keys.length) {
          if (ctx.presenceCard.kind === "verbs") {
            ctx.activatePresenceVerb(keys[slot]);
          } else {
            ctx.activatePresence(keys[slot]);
          }
        }
      }
      return true;
    }
    const descriptor = ctx.router.currentDescriptor();
    if (!descriptor || typeof descriptor.source !== "string" || !descriptor.source.startsWith("exploration.")) {
      return null;
    }
    if (!ctx.railVisible(rs)) {
      return false;
    }
    if (repeat) {
      return true;
    }
    const slots = railSlots(ctx.presenceEntries() || []);
    if (slot < slots.length) {
      ctx.activatePresence(slots[slot].key);
    }
    return true;
  };

  // The commit-time settle (design D2; redesign §7): run at every publish,
  // after the frame stack settles. In order: a mode other than exploration
  // closes the card; a committed move closes it; then, only against an
  // available panel, a verb card whose person is no longer an interact
  // target closes with the `<name> 已經離開了。` flash, and an overflow card
  // with nothing left to fold closes quietly. While a submission is in
  // flight or awaiting its revision the departure check waits: 交談 can
  // commit an intermediate exploration state before the dialogue commit, and
  // the card (with its standee) must hold until that settles.
  ctx.settlePresence = function settlePresence(rs) {
    const card = ctx.presenceCard;
    if (card === null) {
      return;
    }
    if (rs.mode !== "exploration") {
      ctx.presenceCard = null;
      return;
    }
    const location = currentLocation(rs);
    if (isMove(card.location, location)) {
      ctx.presenceCard = null;
      return;
    }
    if (location !== null) {
      // Learn the room or node the card did not know yet, never forget one.
      card.location = {
        room: location.room,
        node: location.node ?? (card.location ? card.location.node : null),
      };
    }
    const entries = ctx.presenceEntries();
    if (entries === null) {
      return;
    }
    if (card.kind === "overflow") {
      if (entries.length <= RAIL_MAX) {
        ctx.presenceCard = null;
      }
      return;
    }
    if (ctx.explorationSubmitLocked()) {
      return;
    }
    const present = entries.some((entry) => entry.presence === "target" && entry.identity === card.identity);
    if (!present) {
      ctx.presenceCard = null;
      ctx.presenceNoticeSeq += 1;
      ctx.presenceNotice = { seq: ctx.presenceNoticeSeq, name: card.name };
    }
  };

  // Drop the slice without publishing (a root reset or a new transport).
  ctx.resetPresence = function resetPresence() {
    ctx.presenceCard = null;
  };

  // The view slice.
  ctx.presenceView = function presenceView(rs) {
    const entries = ctx.presenceEntries();
    const card = ctx.presenceCard;
    let verbs = null;
    if (card && card.kind === "verbs") {
      const menu = ctx.frameResolver.explorationVerbs(card.identity);
      verbs = menu && Array.isArray(menu.items) ? menu.items : null;
    }
    return {
      presenceEntries: entries || [],
      presenceCard: card ? { ...card } : null,
      presenceVerbs: verbs,
      presenceNotice: ctx.presenceNotice,
      railVisible: ctx.railVisible(rs),
    };
  };
}
