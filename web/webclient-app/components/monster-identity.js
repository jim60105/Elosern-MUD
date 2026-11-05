// How a monster's identity reads (monster-individual-names design D5): the
// only place that composes the variant tag. Pure: the server sends the
// `monster_identity` facts (`null`, or exactly `individual_name` (nullable),
// `species_name` and `variant_name`) and never a composed string.

// True when the identity carries the individual's own name.
export function isNamedMonster(identity) {
  return (
    !!identity &&
    typeof identity === "object" &&
    typeof identity.individual_name === "string" &&
    identity.individual_name.length > 0
  );
}

// The detail tag the hover readout, the target prompt and the plate's title
// show: the variant name for an unnamed individual, the variant name followed
// by the species name for a named one, and null without an identity.
export function monsterDetailTag(identity) {
  if (!identity || typeof identity !== "object" || typeof identity.variant_name !== "string") {
    return null;
  }
  return isNamedMonster(identity) ? `${identity.variant_name}${identity.species_name}` : identity.variant_name;
}
