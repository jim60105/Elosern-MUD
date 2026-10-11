# Bestiary editorial review ledger

Indexed editorial review of the current bestiary publication
(`docs/lore/bestiary.md`). The published prose stays authored and freely
editable; this ledger records that a reviewer read each current species section
and what that review covered, so completeness is proved without pinning a single
sentence, and no test ever compares prose.

One entry per shipped species key. Each entry carries the review date, one
disposition for every reviewed face - the ecology narrative, the ability limits,
and the separation between the historical approval appendices and the current
section - plus the overall disposition. Update the entry in the same change that
rewrites a species' current section; a new species has to arrive with its entry,
because the structural check in
`world/lore/tests/test_bestiary_documentation.py` requires exactly one dated,
fully dispositioned entry per shipped species key and rejects an entry for a key
the registry does not ship.

What this ledger does and does not prove: it proves that every current species
was reviewed on a stated date with a recorded disposition for each face. It does
not judge prose quality, does not detect two contradicting passages, and does
not establish that a review is still fresh after a later content edit - those
remain editorial responsibilities, and no test asserts them.

| species key | reviewed | ecology narrative | ability limits | historic vs current | disposition |
| --- | --- | --- | --- | --- | --- |
| `sway_whistle_sparrow` | 2026-10-10 | read against the registry's published ecology field; the harvest-period trouble it describes is local and non-catastrophic | checked against the declared kit: the contact peck is close-range and its boundary text keeps the ability off carts, crops and storms | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: narrative, boundary and delivery status agree |
| `tide_lamp_crab` | 2026-10-10 | read against the registry's published ecology field; the light-following markings stay an observation, not a hazard to settlements | checked against the declared kit: the claw is a close-range strike whose guard does not depend on any light source, and the boundary text denies illusion and healing | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: narrative, boundary and delivery status agree |
| `ridge_burrow_hare` | 2026-10-10 | read against the registry's published ecology field; burrow damage stays local and reversible | checked against the narrative boundary only: no kit is declared, so no executable ability may be read out of the prose, and the boundary text keeps the burrowing out of bedrock and walls | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: narrative and boundary agree; delivery stays narrative-only |
| `rock_echo_goat` | 2026-10-10 | read against the registry's published ecology field; the hazard is confined to already-loose rock on working slopes | checked against the narrative boundary only: no kit is declared, and the boundary text refuses quarry-scale collapses and wide-area tremor | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: narrative and boundary agree; delivery stays narrative-only |
| `fog_mane_lynx` | 2026-10-10 | read against the registry's published ecology field; its conflict stays with hunters and pack animals on a known route | checked against the narrative boundary only: no kit is declared, and the boundary text keeps it visible by tracks, scent and sound rather than invisible | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: narrative and boundary agree; delivery stays narrative-only |
| `tide_devouring_crocodile` | 2026-10-10 | read against the registry's published ecology field; the trouble is a local waterway hazard, not a region-wide threat | checked against the declared kit: the drain needs contact, credits only what it actually removes, and the boundary text denies ranged draining and wound healing | current section read as current; the dated delivery appendices are behind the boundary marker and claim no current coverage | accepted: narrative, boundary and delivery status agree |
