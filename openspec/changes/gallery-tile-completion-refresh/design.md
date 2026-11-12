# Design: refresh gallery wall tiles on art completion

## Context

`web/webclient/presentation/art_push.py::_panel_matches_subject(panel_name,
payload, subject_key)` re-renders each panel for a session and qualifies
`gallery` through `_gallery_subject_keys(payload)`, which returns only
`{payload["selected"]}`. Its docstring cites "D2: gallery matches on rendered
selected only, not every rail subjects entry".

## Goals / Non-Goals

**Goals:** listed subjects qualify. **Non-Goals:** any other panel's
qualification; collapsed people groups (their subjects are not rendered and
therefore do not qualify — correct, since no tile shows them).

## Decisions

```python
def _gallery_subject_keys(payload):
    keys = set()
    selected = payload.get("selected")
    if isinstance(selected, str) and selected:
        keys.add(selected)
    for group in payload.get("groups") or []:
        if isinstance(group, dict):
            for row in group.get("subjects") or []:
                if isinstance(row, dict) and isinstance(row.get("subject_key"), str) and row["subject_key"]:
                    keys.add(row["subject_key"])
    return keys
```

Update the docstring to cite this change. Gating stays on the freshly rendered
payload, so an unlisted subject still does not qualify.

## Risks / Trade-offs

- [More gallery pushes for sessions with large walls] → one per completion per
  session at most, the same bound as today's selected-subject push.
