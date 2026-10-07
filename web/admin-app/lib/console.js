// The closed transport vocabulary. Balance bounds remain server-owned.
export const VERB_FIELDS = Object.freeze({
  give_item: ['key', 'quantity'], take_item: ['key', 'quantity'], set_wallet: ['copper'],
  set_trait_base: ['trait', 'value'], set_gauge: ['gauge', 'value'], advance_clock: ['seconds'],
  teleport: ['room'], spawn_monster: ['species', 'variant'], delete_entity: [],
  set_quest_state: ['quest_id', 'state'], set_quest_stage: ['quest_id', 'stage'],
  issue_quest: ['definition_key', 'issuer_key'], retract_memory: ['memory_id'],
  supersede_memory: ['memory_id', 'replacement_id'],
});
export const KIND_VERBS = Object.freeze({
  characters: ['give_item', 'take_item', 'set_wallet', 'set_trait_base', 'set_gauge', 'teleport', 'set_quest_state', 'set_quest_stage', 'issue_quest'],
  monsters: ['set_trait_base', 'set_gauge', 'teleport', 'delete_entity'],
  rooms: ['spawn_monster'],
});
export const NUMERIC_FIELDS = new Set(['quantity', 'copper', 'value', 'seconds', 'stage', 'memory_id', 'replacement_id']);
export function argumentsFor(verb, target, draft) {
  const args = Object.fromEntries(VERB_FIELDS[verb].map(key => [key, NUMERIC_FIELDS.has(key) ? Number(draft[key]) : draft[key]]));
  if (verb === 'spawn_monster') args.room = target;
  else if (verb !== 'advance_clock') args.target = target;
  return args;
}
export function saveNotice(status) {
  if (!status) return '正在確認存檔政策…';
  if (status.tick === null) return '世界時鐘尚未建立，無法執行操作。';
  if (status.baseline_tick === null) return '這是本次啟動後的首次介入，執行前需要存檔。';
  return status.will_snapshot ? '遊戲內時間已變更，執行前需要存檔。' : '遊戲內時間未變更，本次不另存檔。';
}
