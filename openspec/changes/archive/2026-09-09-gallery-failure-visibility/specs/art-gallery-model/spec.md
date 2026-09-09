## ADDED Requirements

### Requirement: The recorded generation error is last-attempt state, not a permanent mark
The generation error a `GalleryRecord` carries SHALL describe the subject's LAST generation attempt.
Recording an error SHALL replace any previously recorded code and timestamp, and `world/art/gallery.py`
SHALL expose a clearing operation that resets both to `None`. Clearing a subject that has no record
SHALL be a side-effect-free no-op — it SHALL NOT create a record, because a subject that never failed
has nothing to clear. Both operations SHALL run under the same `gallery_lock` as every other record
mutation and SHALL emit their existing bounded facade events.

#### Scenario: A second failure replaces the first code
- **WHEN** a subject records error code `A` and later records error code `B`
- **THEN** the record carries `B` with `B`'s timestamp and no trace of `A`

#### Scenario: Clearing a subject with no record creates nothing
- **WHEN** the recorded error is cleared for a subject that has never been written
- **THEN** no record is created, no error is raised, and the subject still reads as an empty gallery

#### Scenario: Clearing leaves every card untouched
- **WHEN** the recorded error is cleared for a subject holding cards and a default
- **THEN** the error code and timestamp are `None` and the card list and `default_image_id` are unchanged

### Requirement: One read-only accessor reports every subject whose gallery carries an error
`world/art/gallery.py` SHALL expose one read-only accessor returning the subjects whose record carries
a recorded generation error, each with its bounded code and timestamp. The single-writer rule keeps the
record class inside that module, so operator surfaces SHALL read cross-record gallery state ONLY
through the gallery module's read-only accessors and SHALL NOT query the record class themselves. The
erroring-subject accessor is the sole cross-record ERROR read; the gallery module MAY expose additional
read-only accessors of the same discipline (for example per-record state summaries for the staff status
surface). Every such accessor SHALL create no record, SHALL write nothing, and SHALL be tolerant: a
record whose persisted kind or subject key no longer parses SHALL be skipped rather than raising, so one
corrupt row can never blind the whole surface.

#### Scenario: Only erroring subjects are reported
- **WHEN** the accessor runs against a store holding one subject with a recorded error and two without
- **THEN** exactly the erroring subject is returned, with its code and timestamp

#### Scenario: The accessor never writes
- **WHEN** the accessor runs against a store with no gallery records at all
- **THEN** it returns nothing, creates no record, and raises no error

#### Scenario: An unparseable record is skipped, not fatal
- **WHEN** the accessor runs against a store where one gallery record's persisted subject no longer parses
- **THEN** that row is skipped, every other erroring subject is still returned, and no exception escapes
