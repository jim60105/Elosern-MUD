// The single dispatch seam shared by every surface group (webclient-action-feedback):
// AppClient creates it once and threads it through the composable groups so the
// busy-drop toast contract has exactly one implementation.
import { useElosernStore } from "../stores/elosern.js";

export function useDispatchIntent(store = useElosernStore()) {
  // webclient-action-feedback (busy-drop feedback): dispatchAction returns null
  // when the single-writer gate refuses the dispatch (an in-flight action, a
  // locked mutation phase, or a disconnected session). Surfaces that fire and
  // forget would otherwise silently swallow the player's deliberate activation,
  // so every ignored-return dispatch routes through this helper, which leaves a
  // visible busy toast at the client boundary instead of dropping it silently.
  // Return-bearing seams (the concept apply) keep calling the store directly.
  function dispatchIntent(actionId, payload, display) {
    const request = store.dispatchAction(actionId, payload, display);
    if (request === null) {
      store.pushToast({ title: "目前無法執行此操作，請稍後再試。", tone: "info" });
    }
    return request;
  }
  return { dispatchIntent };
}

// Panel action intents (C4: every surface's emitted intent routes through
// the single store dispatch entry — no component mutates state directly).
export function useIntentHandlers(store, dispatchIntent) {
  function onShopBuy(intent) {
    dispatchIntent(intent.action_id, intent.payload);
  }

  function onShopSell(intent) {
    dispatchIntent(intent.action_id, intent.payload);
  }

  // Inventory row-action intents (add-inventory-item-actions, task 6.3): both
  // the confirmed item use and the direct equipment toggle route through the
  // single store dispatch entry — one deliberate activation, one dispatch.
  function onInventoryItemAction(intent) {
    dispatchIntent(intent.action_id, intent.payload);
  }

  // The pending 異名提名 ballot (title-epithet-nomination): the menu's
  // accept/decline intents ride the same single dispatch entry as the shop
  // and quest surfaces.
  function onTitleBallotAction(intent) {
    dispatchIntent(intent.action_id, intent.payload);
  }

  // The 稱號冊 window (title-codex-removal): equip/remove/ballot intents ride
  // the same single dispatch entry; the rules writer re-validates every gate
  // at execution, so the window forwards without client-side rules.
  function onTitleCodexAction(intent) {
    dispatchIntent(intent.action_id, intent.payload);
  }

  function onCreationAction(intent) {
    dispatchIntent(intent.action_id, intent.payload);
  }

  // The return-bearing dispatch seam (retool-concept-fill-navigation D1a): the
  // concept apply needs the admission result (requestId / null) to gate its
  // loading state; every other creation intent keeps the fire-and-forget route.
  function onCreationDispatch(intent) {
    return store.dispatchAction(intent.action_id, intent.payload);
  }

  function onCreationRequestReset() {
    store.requestCreationReset();
  }

  function onCreationCancelConfirm() {
    store.focusEscape();
  }

  function onQuestAction(intent) {
    dispatchIntent(intent.action_id, intent.payload);
  }

  // add-persona-edit-surface: one drawer persona edit submits exactly one
  // character.persona.update action with the section's field key and the
  // edited text (null clears).
  function onPersonaEdit(intent) {
    dispatchIntent("character.persona.update", { field: intent.field, text: intent.text });
  }

  function onSubmitCommand(text) {
    // Ordinary text path: the store sends it through the single transport
    // seam (`sender.sendText` -> `Evennia.msg("text", ...)`).
    return store.sendText(text);
  }

  // MC5 (multichar-05-topbar-switcher-ui): route character switch/create actions
  // through the store's single dispatchAction entry point.
  function onSwitchCharacter(characterId) {
    store.dispatchAction("account.character.switch", { character_id: characterId });
  }

  function onCreateCharacter() {
    store.dispatchAction("account.character.create", {});
  }

  return {
    onCreationAction,
    onCreationCancelConfirm,
    onCreationDispatch,
    onCreationRequestReset,
    onCreateCharacter,
    onInventoryItemAction,
    onPersonaEdit,
    onQuestAction,
    onShopBuy,
    onShopSell,
    onSwitchCharacter,
    onTitleBallotAction,
    onTitleCodexAction,
    onSubmitCommand,
  };
}
