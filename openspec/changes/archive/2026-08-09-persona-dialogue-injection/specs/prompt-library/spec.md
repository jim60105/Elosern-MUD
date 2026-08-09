## MODIFIED Requirements

### Requirement: Prompt rendering substitutes only allowlisted placeholders deterministically
`world/prompts` SHALL expose `render_prompt(key, **values) -> str` that returns the key's loaded
text with only its allowlisted `{token}` placeholders replaced by the supplied string values,
using exact `{token}` matching. A token SHALL NOT be substituted when it is adjacent to another
brace, so `{{name}}` and JSON example braces such as `{"name": "…"}` pass through untouched.
Supplied values whose names are not in the key's allowlist SHALL be rejected with a named error,
never silently ignored, so a consumer typo such as `namme=` fails loudly. Identical text and
values SHALL produce byte-identical output, and substitution SHALL be complete: every present
allowlisted token SHALL be replaced exactly once. The `npc_dialogue.system` key's allowlist SHALL
be exactly `name`, `desc`, `location`, and `persona`. Callers of `npc_dialogue.system` SHALL pass
`persona` on every call — the flattened block when one exists, or an empty string when not — so
the `{persona}` token is always substituted and never left literal in rendered output.

#### Scenario: Allowlisted placeholders are substituted
- **WHEN** `render_prompt("npc_dialogue.system", name="艾洛西亞", desc="…", location="王都",
  persona="性格：…")` is called
- **THEN** the returned text contains the supplied values in place of `{name}`, `{desc}`,
  `{location}`, and `{persona}` exactly once each

#### Scenario: An empty persona value substitutes without error
- **WHEN** `render_prompt("npc_dialogue.system", name="艾洛西亞", desc="…", location="王都",
  persona="")` is called
- **THEN** the render succeeds and the `{persona}` token is replaced by the empty string — the
  output equals the template text with only the identity placeholders filled, with no literal
  `{persona}` remaining and no error raised

#### Scenario: JSON braces in a prompt pass through untouched
- **WHEN** a prompt containing `{"name": "…", "items": [{"item_key": "healing_potion"}]}` is
  rendered with no matching placeholder values
- **THEN** the braces and JSON structure are unchanged in the output

#### Scenario: Double-braced tokens are literal text, not placeholders
- **WHEN** a prompt contains `{{name}}` or `{{location}}`
- **THEN** those tokens are emitted literally, never substituted, regardless of supplied values

#### Scenario: A placeholder outside the allowlist is rejected
- **WHEN** a prompt text contains a `{token}` not in the key's allowlist
- **THEN** the loader rejects that key with a named `PromptLibraryError` naming the file, key,
  and placeholder, and the key is marked unavailable without aborting startup

#### Scenario: An unknown supplied value name is rejected
- **WHEN** `render_prompt()` is called with a value whose name is not in the key's allowlist
- **THEN** a named error is raised and the value is never silently ignored
