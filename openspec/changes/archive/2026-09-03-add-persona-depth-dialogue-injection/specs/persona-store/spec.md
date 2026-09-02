# persona-store — Delta Spec

## MODIFIED Requirements

### Requirement: Flatten produces one bounded, labeled prompt block
`PersonaStore.flatten(fields=("personality", "life_story", "habit"))` SHALL return a single string with one labeled section per present field in the declared field order (e.g. 性格：… / 人生經歷：… / 習慣：…, and 背景：… for a `background` field), each field string capped and the combined block capped at a total bound. A missing record, a non-mapping record, or a record with none of the requested fields renderable SHALL return `None` and never raise. The default field set (and therefore the default NPC dialogue injection path) remains the three prose fields; `background` is included only when explicitly requested. Rendering SHALL be tolerant of stored shapes: a non-empty string renders verbatim after capping; a Mapping renders as one `子鍵：值` line per renderable entry in declared-key order for known key groups (`identity` → public then hidden; `appearance` → height, weight, measurement, style, overview, attire, feature) with unrecognized sub-keys following, using the localized sub-key labels where defined and the raw key otherwise; a list or tuple renders as dash-prefixed item lines; deeper nesting stringifies as a final fallback; a value of any other shape (number, boolean, null) is skipped without raising. The structural keys SHALL carry localized labels — `identity` as 身分 (a Mapping rendering its public and hidden entries as 公開身分 and 隱秘身分 lines, a plain string rendering as a single 身分 section), `appearance` as 外觀, and `social_connection` as 人脈 with each entry keyed by its counterparty name — and every rendered section SHALL pass through the same per-field and whole-block caps as the prose fields. `PersonaStore` SHALL additionally expose a read-only `public_view()` returning a new store over a copy of the record in which a mapping-valued `identity` is rebuilt into an independent hidden-free snapshot: every `hidden`-keyed mapping entry is pruned at any depth, every nested container is freshly copied (so later mutation of the stored record cannot re-introduce hidden content), and cycle back-references are dropped from the copy (a string-valued `identity` and any non-mapping record pass through verbatim), so callers flatten a hidden-free view by construction without mutating or re-reading the stored record.

#### Scenario: Three present fields flatten in declared order with labels
- **WHEN** a record contains all three fields and `flatten()` is called with the default fields
- **THEN** the result is one string containing exactly three labeled sections in the order `personality`, `life_story`, `habit`, each label prefix present once

#### Scenario: An explicitly requested background flattens with its label
- **WHEN** a record contains a non-empty `background` and `flatten(("personality", "life_story", "habit", "background"))` is called
- **THEN** the result includes a `背景：` labeled section carrying the capped background text, in the requested field order

#### Scenario: Absent fields are omitted
- **WHEN** a record contains only `personality` and `habit`
- **THEN** the flattened block contains exactly two labeled sections and no placeholder or empty section for `life_story`

#### Scenario: Scalar non-string fields are treated as absent
- **WHEN** a record field such as `habit` is `None`, a number, or a boolean
- **THEN** that field produces no section and no exception is raised

#### Scenario: A nested mapping renders as labeled sub-key lines
- **WHEN** `identity` holds `{public: …, hidden: …}` and `flatten` is called with a field set including `identity`
- **THEN** the section carries the 公開身分 and 隱秘身分 lines with their capped values and raises nothing

#### Scenario: A string-shaped structural key still renders
- **WHEN** `identity` holds a plain string (an import-example-style flattened value)
- **THEN** the section renders as a single 身分 section carrying that capped text

#### Scenario: Lists render as dashed item lines
- **WHEN** `appearance`'s `feature` (or any list-valued entry) holds a list of strings
- **THEN** those items render as dash-prefixed lines inside the parent section without raising

#### Scenario: Unknown shapes are skipped
- **WHEN** a structural sub-key holds a number, boolean, or null
- **THEN** that sub-key contributes no line, the rest of the section renders, and no exception is raised

#### Scenario: Missing or malformed records return None
- **WHEN** `flatten()` is called for an entity with no persona record, a non-mapping persona value, or a mapping with none of the requested fields renderable
- **THEN** the result is `None` and no exception is raised

#### Scenario: Field and block caps are enforced deterministically
- **WHEN** a rendered field string or the combined block exceeds the configured bounds
- **THEN** the result is truncated to the bound; the truncation is deterministic and never raises

#### Scenario: Public view drops the hidden identity layer
- **WHEN** `public_view()` is called on a store whose record carries a mapping `identity` with `public` and `hidden` entries, and the returned store is flattened over a field set including `identity`
- **THEN** the block carries the 公開身分 line with no 隱秘身分 line and no hidden value, the underlying record is byte-for-byte unmodified, and the handler still exposes no write API

#### Scenario: Public view prunes nested hidden entries and resists later mutation
- **WHEN** a record's `identity` nests a mapping or list below its `public` layer that itself holds a `hidden` entry, and the stored record's nested containers are mutated toward hidden keys after `public_view()` was taken
- **THEN** no hidden-keyed value at any depth appears in the view's flattened block, the view output is unchanged by those later mutations, and cyclic containers degrade to a dropped branch instead of raising
