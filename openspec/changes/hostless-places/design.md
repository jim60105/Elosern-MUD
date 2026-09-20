## Context

`PlaceDefinition` has eight host fields and all eight are required. `validate_service_hosts` iterates `PLACE_REGISTRY.values()` unconditionally and derives one `ServiceHostRow` per place. The registry therefore cannot describe a room that simply exists.

The source document asks for exactly that in three places, and the capital replan asks for more: scenery that makes a city feel like a city rather than a corridor of shopfronts.

## Goals / Non-Goals

**Goals.** A place may author no host. The interior still gets built. A half-authored host is caught at load rather than producing a nameless NPC.

**Non-Goals.** No change to how hosts that *are* authored behave. No new room typeclass — a host-less interior is the same ordinary permanent room every other interior is. No scenery-specific `PlaceKind`; kind stays a description of what the location is, and a landmark takes whichever kind fits.

## Decisions

### All-or-nothing, not field-by-field

The tempting shape is "each host field defaults to `None`, validate what is present". That admits a place with a name and no profession, which produces either a crash downstream or an NPC with no components. The fields are one unit because they describe one thing.

The check is stated over the whole set: count how many of the eight are authored; zero and eight are legal, anything between is an error that names which fields were found and which were missing. That error message is the whole value of the rule — the failure mode it replaces is a `None` profession key reaching `get_profession` several layers away.

`host_subrace` is the exception and must stay outside the count: `None` is a legitimate authored value for it (every capital host authors `None` today). The set is the other six — name, title, race, sex, profession, service id — and `host_subrace` is validated only when those six are present.

### Every field after the first default needs one

The dataclass has no `kw_only`, so defaulting the host fields forces a default onto everything declared after them. That is `assortment_keys` and `authored_kwargs`, and `assortment_keys` is the trap: it sits between `service_id` and `authored_kwargs`, so a change that defaults the host fields and `authored_kwargs` but skips it fails at import with `TypeError: non-default argument 'assortment_keys' follows default argument`. Not a subtle bug — the module will not load — but the kind of thing a task list omits and an implementer rediscovers.

`assortment_keys = ()` is also correct on its own terms: `validate_place_registry` already reads an empty tuple as "declares no goods".

### The roster comprehension, not a new registry

`validate_service_hosts` gains a skip, not a second registry of "host-bearing places". A derived view with a filter is still one source of truth; a parallel registry would be two.

The skip goes at the top of the loop and is stated positively — iterate places, continue past the host-less ones — so the function keeps reading as "one row per place that declares a host".

### `PlaceKind` is untouched

A palace forecourt could be argued into a new `LANDMARK` kind. Rejected: `PlaceKind` already carries `HOME`, which the elven village uses for four dwellings that are also shops. Kind describes the location's nature, not whether someone works there. Adding a kind that means "no host" would encode the host question twice — once in the kind and once in the fields — and the two would eventually disagree.

## Risks

**A content author omits a host by accident and gets a silent empty room.** The all-or-nothing rule catches a half-authored host but cannot catch a wholly forgotten one. Accepted: the same is true of a forgotten place row. Mitigated by the downstream content changes asserting host counts per settlement, so a vanished host shows up as a count mismatch rather than as an empty room nobody visits.

**`_place_for_shop` scans places for a `shop_key`.** A host-less place has no `authored_kwargs` at all, so `dict(place.authored_kwargs)` must not be called on `None`. The field defaults to an empty tuple rather than `None` for exactly this reason — the scan keeps working unmodified, finds nothing, and the goods-need-a-host rule guarantees there was nothing to find.
