# Tasks

All tasks are future implementation, with Shared contract v2 fixed beforehand. Three 60-120 minute units fit one GPT-Luna workday. Runtime owns the later live table cutover.

## 1. Safe sorted discovery

- [x] 1.1 Implement loader.py safe direct-file scan and duplicate-key/tag/alias/document/path/UTF-8/size rejection. Add synthetic temp-directory tests for each rejecting input and sorted discovery; document the filename ownership/no-registration contract in the module and existing author docs.

## 2. Common validation and atomic snapshot

- [x] 2.1 Derive existing canonical profile/dialogue binding, parse through the common codec/reference catalog and freeze the whole candidate before returning one read-only snapshot. Test guild_staff/profile-key distinction, invalid-neighbor all-or-nothing behavior, duplicate bindings, unknown profile/reference and attempted nested mutation; document failure ownership and generated DB exclusion.

## 3. Discoverability and handoff acceptance

- [x] 3.1 Prove a new valid registered-profile file appears with no registration edit, equivalent YAML/JSON primitives share validation, and test-only reload does not introduce production hot reload. Register test ownership and run the focused commands in design.md plus contract_gate; no prose migration or runtime changes in this slice.
