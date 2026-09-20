"""
Creation action adapter and dispatcher integration tests (tasks 3.3-3.4).

Exercises every one of the four production creation adapters against real
Evennia state: success (preset selection, custom preflight-and-save, atomic
activation with the exploration hand-off, idempotent reset), every
deterministic domain rejection, tampered/authority-like fields rejected before
the domain API, dispatcher-level stale and duplicate handling, a before/after
assertion that no canonical surface changes on rejection, and the all-or-
nothing ``activate_draft`` outer transaction.

Registry identities come from the synthetic kit (P17's creation-panel idiom):
every Evennia-backed class runs inside a creation scope over races, subraces,
static tiers, starting kits, and presets, so custom saves, preset activation
(kit inventory), and the name-roll semantic gate all resolve kit rows. The affinity bound map is production state keyed by race (not a kit
registry), so the kit race gets a patch entry; the elf branch of the adapter
keys off the literal ``elf`` race, so the suite borrows an in-scope ``elf``
profile like the rule-layer affinity suite. The element registry stays
shipped: the adapter's affinity membership resolves against it and the
element-key claims are shipped wire vocabulary (the P17 creation-panel
idiom). The name-pack corpus stays live: the roller's fallback candidate list
is snapshotted from the shipped binding map at its import time (outside the
kit's per-target patching), and the bound-pack claim is about that
production corpus; the registry is reached through a runtime probe, never an
import-time symbol.

Package split of the original flat module; each slice module groups
the shipped classes by concern. Shared module-level helpers live
in ``_support`` (not a collected test module).
"""
