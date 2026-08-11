## Context

`_validate_subject_key` (`world/art/subjects.py:48-57`) rejects only `:` and control characters; the import schema (`world/imports/schema.py:45`) has no pattern/length; the worker embeds the raw key into the output path (`world/art/worker.py:71-77`), the media route requires a single filename segment (`web/art_media.py:20-22`), and the wire caps subject keys at 128 (`web/webclient/presentation/art.py:51`). `claim` persists `IN_PROGRESS` (`world/art/queue.py:168`, `store.py:18`), the presenter emits it verbatim (`presenter.py:69-80`), and both wire allowlists accept only missing/pending/failed/done (`art.py:110-113,176-180`; `protocol.js:2569-2637`), so any snapshot during a claim degrades the panel.

## Goals / Non-Goals

**Goals:**
- One key contract that every accepted key can survive (queue, file path, media URL, wire).
- Panel stays available during generation.

**Non-Goals:**
- Hashing/encoding filename identities (keys are now bounded and safe by contract).
- Changing the worker's atomic write/settle flow.

## Decisions

**D1 — Tighten `_validate_subject_key`** to reject `|`, `/`, `:`, `{`, `}`, and control characters, and keys longer than 64 characters; enforce the same rule at import validation (`world/imports/validate.py`) and quest characterization so invalid keys never reach the queue. This is the single shared key contract; the import/creation changes (`fix-import-key-validity`) mirror it.

**D2 — Wire length covers the full subject key.** The wire `subject_key` carries the full form (`<kind>:<key>`), so `MAX_SUBJECT_KEY` stays 128 and a producer key ≤ 64 plus the longest prefix (`portrait:character:` = 19 chars) always fits. Add a boundary round-trip test for every `ArtSubjectKind`. The media route needs no change because valid keys are single-segment.

**D3 — Normalize `in_progress` → `pending` at the presenter.** A claimed record is presented as `pending` (placeholder behavior), leaving the persistent lifecycle status untouched; `missing/pending/failed/done` pass through unchanged.

## Risks / Trade-offs

- **Longer valid keys in the wild**: project has no users; existing long keys in test data are updated to the new limit.
- **Normalization hides in-flight state from the client**: the placeholder is identical to pending — acceptable and matches the wire contract; a future explicit `generating` state can extend both sides later.
