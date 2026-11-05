// Synthetic fixtures for the monster-names prototype (reference only). The
// identity objects mirror the `monster_identity` wire shape of
// docs/superpowers/specs/2026-11-05-monster-individual-names-design.md.
import { FOE_PORTRAIT_CATALOG } from "../../../web/webclient-app/stories/fixtures/combat_stage.js";

export const NAMED_KEY = "target-named";
export const NAMED_IDENTITY = 7001;

const portraitRef = Object.keys(FOE_PORTRAIT_CATALOG)[0];

export const ART_PANEL = {
  schema_version: 2,
  available: true,
  kind: "scene",
  scene: null,
  portrait_catalog: FOE_PORTRAIT_CATALOG,
};

const NAMED = { individual_name: "閉灣者", species_name: "吞潮鱷", variant_name: "守灣型" };
const GUARD = { individual_name: null, species_name: "潮燈蟹", variant_name: "守礁型" };
const WALKER = { individual_name: null, species_name: "潮燈蟹", variant_name: "灘行型" };
const SLIME = { individual_name: null, species_name: "泥膜史萊姆", variant_name: "濕岸型" };

export const monsterName = (identity) => identity.individual_name ?? identity.species_name;

// The client's only reading of identity (the spec's `monsterDetailTag`).
export const monsterDetailTag = (identity) =>
  identity.individual_name === null
    ? identity.variant_name
    : `${identity.variant_name}${identity.species_name}`;

function entry(key, identity, summary) {
  return {
    key,
    presence: "target",
    label: monsterName(identity),
    summary,
    identity,
    enabled: true,
    actionId: null,
    payload: null,
    portraitRef,
  };
}

export const RAIL_ENTRIES = [
  entry(NAMED_KEY, NAMED, "盤踞灣口的巨鱷，封住了整片潮間帶。"),
  entry("target-guard", GUARD, "查看、交戰"),
  entry("target-walker", WALKER, "查看、交戰"),
  entry("target-slime", SLIME, "查看、交戰"),
];

export const FOES = [
  { id: 7002, identity: GUARD, token: "e1", hp: 44, max: 60, x: 0.5, h: 0.5 },
  { id: NAMED_IDENTITY, identity: NAMED, token: "e2", hp: 318, max: 420, x: 0.68, h: 0.9 },
  { id: 7003, identity: WALKER, token: "e3", hp: 6, max: 30, x: 0.86, h: 0.42 },
];

// The longest name the bound allows, to prove the plate treatment fits it.
export const LONG_NAMED = {
  id: 7011,
  identity: { individual_name: "潮眠守灣者", species_name: "吞潮鱷", variant_name: "守灣型" },
  token: "e4",
  hp: 210,
  max: 420,
};
