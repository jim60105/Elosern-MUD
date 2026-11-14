// The landmark rite surfaces' pure model (landmark-rite-surfaces design D2).
// It reads the committed `rite` panel (landmark-rite-panel D1) and derives
// what RitePanel renders; it builds no wire payload and holds no state.

export const SOLO_ONLY_REASON = "這個儀式只能親自進行";
export const UNSEEN_LABEL = "尚未體驗";

// The performer rows of a rite panel: {id, memberId, name, self}. id is "self" for the first row (the controlled
// character, member_id null), else String(member_id). self is the row's `owner` flag: only the record owner's own
// body performs in the first person, so a possessed companion in the first row has self false.
export function ritePerformers(rite) {
  return rite.performers.map((performer, index) => ({
    id: index === 0 ? "self" : String(performer.member_id),
    memberId: performer.member_id,
    name: performer.name,
    self: performer.owner === true,
  }));
}

// The rite panel's ChoiceCard rows for one performer: one digit row per
// option in order, then 退開 as the back row. While a companion performs, an
// option that does not admit a companion is disabled with its reason and
// carries no unseen mark.
export function riteRows(rite, performer) {
  const rows = rite.options.map((option, index) => {
    const blocked = !performer.self && !option.companion;
    return {
      key: option.key,
      badge: String(index + 1),
      label: option.label,
      enabled: !blocked,
      reason: blocked ? SOLO_ONLY_REASON : null,
      unread: !blocked && !rite.seen.includes(option.key),
    };
  });
  rows.push({ key: "leave", label: "退開", icon: "close", kind: "leave", back: true });
  return rows;
}
