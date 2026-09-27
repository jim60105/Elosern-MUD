// ---- The foe line-up (webclient-combat-foes-on-stage) ----
// Committed combat participants and their `art` catalog entries for the
// line-up's stories. Deterministic offline art: the committed built-in
// fallbacks under `/art/defaults/` stand in for generated portraits, chosen
// for their mix of light and dark backdrops so the depth shadow and the
// gauges are reviewed over both.

function foeEntry(ref, url, name) {
  return {
    subject_key: `npc_${ref}`,
    status: "done",
    url,
    aspect_ratio: "3:4",
    alt: `${name}的肖像`,
    placeholder: null,
    face_rect: { x: 0.3, y: 0.06, w: 0.4, h: 0.36 },
    context: { name, role: "敵方" },
  };
}

// The foes in presenter order: identity, token, name, portrait, hit points.
const FOE_ROSTER = [
  [31, "e1", "灰袍盜賊", "/art/defaults/monster_anon.webp", 42, 60],
  [32, "e2", "盜賊頭目", "/art/defaults/man.webp", 90, 90],
  [33, "e3", "蒙面刺客", "/art/defaults/woman.webp", 18, 50],
  [34, "e4", "見習盜賊", "/art/defaults/boy.webp", 30, 30],
  [35, "e5", "銷贓商人", "/art/defaults/elder.webp", 40, 40],
];

export const FOE_PORTRAIT_CATALOG = Object.freeze(
  Object.fromEntries(FOE_ROSTER.map(([identity, , name, url]) => [String(identity), foeEntry(String(identity), url, name)])),
);

// The first `count` foes as committed combat participants (all active).
export function foeParticipants(count, overrides = {}) {
  return FOE_ROSTER.slice(0, count).map(([identity, token, name, , hp, max]) => ({
    identity,
    token,
    display_name: name,
    team: "foes",
    state: "active",
    hp_current: hp,
    hp_maximum: max,
    portrait_ref: String(identity),
    ...(overrides[identity] || {}),
  }));
}

// The player's side as the combat panel lists it.
export const PARTY_PARTICIPANTS = Object.freeze([
  { identity: 1, token: "a1", display_name: "艾莉亞", team: "party", state: "active", hp_current: 80, hp_maximum: 100, portrait_ref: null },
  { identity: 8, token: "a2", display_name: "同行劍士", team: "party", state: "active", hp_current: 100, hp_maximum: 100, portrait_ref: null },
]);
