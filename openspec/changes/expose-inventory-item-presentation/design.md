## Context

The `services` presentation path currently builds `InventoryRowView(item_key, display_name, held, equipped)`, serializes a strict version-1 payload, validates that payload on both Python and browser boundaries, and stores only validated committed data. Item keys in the canonical flat inventory are structurally valid strings and are not required to exist in `ITEM_REGISTRY`; the current presenter truthfully displays an unknown key as its own name.

`add-item-presentation-metadata` introduces immutable visual identity only for registered keys. This change carries that identity across the existing read-only presentation boundary before a Vue component attempts to consume it.

## Goals / Non-Goals

**Goals:**

- Publish a single validated `presentation` object with every registered inventory row.
- Preserve unknown-key inventory rows without fabricating a category, icon, rarity, summary, or registry identity.
- Reject malformed presentation data before it reaches Pinia or a component.
- Keep the presenter no-create and no-mutation, retaining all existing row and byte ceilings.

**Non-Goals:**

- No item lookup in browser code, client-side inference, item state mutation, or new UI action.
- No projection to stock, sellable, quest reward, text-command, or character equipment rows in this one-day change.
- No numeric attribute, comparison, or tooltip contract.
- No support for services schema version 1 after this change. The project has no released consumers, and every producer and consumer is deployed together.

## Decisions

### Version the strict services payload forward

The services panel advances from schema version 1 to 2. A strict version bump makes the changed inventory row shape unambiguous at the Python protocol validator, browser validator, store, fixtures, and tests. Keeping version 1 and treating `presentation` as optional would permit a UI to silently receive incomplete data, defeating the purpose of a validated presentation contract.

The unavailable discriminator remains its registered common form. It is not an available services-v2 payload and therefore does not need an invented inventory object or presentation fallback.

### Use one nullable projection field for registered versus unregistered keys

Each inventory row gains exactly one `presentation` member. For a registry key, it is an exact object with `kind`, `icon_key`, `rarity`, and `summary`; all values are copied from the immutable registry without transformation. For an unknown but structurally valid key, it is `null`.

Rejecting unknown keys was considered but would change the canonical inventory contract, which permits structurally valid non-registry keys and existing callers may legitimately carry them. Substituting a guessed `misc` object was rejected because it would fabricate a registry classification. The later UI may render a neutral unknown-item state only when this field is null.

### Keep the server vocabulary opaque to the browser protocol validator

The browser validator checks bounded string syntax and the exact object shape, but the Python presenter enforces that values came from the closed immutable enums. This separates wire safety from server ownership of the registry. The Vue renderer owns a matching closed SVG map and must fail safely with a labelled neutral glyph if an otherwise schema-valid future enum value reaches it.

### Preserve current aggregation and no-action semantics

The projection happens after the existing `Counter` aggregation and equipment key lookup. It neither reads a lazy stateful handler nor changes item order, count, equipped flag, pagination, wallet, or any action descriptor. `presentation` consumes part of the existing 65,536-byte services envelope; bounds on the summary and closed identifiers keep the worst-case payload safely bounded.

## Risks / Trade-offs

- [All schema validators and fixtures must move in lockstep] -> Change the server serializer, Python validator, Node validator, fixtures, store tests, and Vue stories in one atomic PR; no dual-read path is retained.
- [A large bounded inventory may approach the envelope ceiling] -> Extend the existing maximal-payload regression to include maximal valid presentation summaries and assert the canonical JSON byte gate remains authoritative.
- [Unknown inventory keys cannot receive the new visual treatment] -> Emit explicit `null` so the UI can label an unknown item without making a false metadata claim; a future registry addition begins presenting it automatically.
- [A server/client enum drift produces an unrecognised glyph] -> Test the registry-to-protocol path and require the later renderer to provide a neutral labelled fallback instead of an arbitrary asset.

## Migration Plan

Land only after `add-item-presentation-metadata`. Update the producer and every in-repository consumer in the same deployment, run the focused Python and Node protocol gates, and publish only services version 2. A rollback deploys the former server and client together; no persistent data, stored snapshot, or user configuration requires conversion.
