# Proposal: art-service-connectivity-surface

## Why

The reference plugin treats "is sd-webui actually reachable right now?" as a
first-class, user-visible concern: it runs a fast `GET /sdapi/v1/samplers`
connectivity probe (its own 2 s budget) through the same transport as real
calls, caches the verdict in a TTL cache keyed by the effective configuration
so the UI badge flips to "offline" instantly and stays honest across
credential/URL edits, and exposes an explicit **Test connection** action that
bypasses the cache. We have none of this: when sd-webui is down, the only way
an operator learns it is reading `@art status` failure rows after the worker
has already burned attempts, and there is no way to ask "server reachable?
queue state? which settings are live?" in one answer.

A connectivity surface is also where the reference keeps its SSRF host-policy
and DNS-pinning machinery. We deliberately do NOT adopt those: Elosern's
`ART_SD_BASE_URL` is operator-authored in a settings/secret file, never a
user-supplied value — the threat class the plugin defends against (a chat
user steering the URL) does not exist here. What we adopt instead is the
reference's **probe + cached-flag + explicit check** behavior, translated to
our idiom (env knobs + one staff command).

## What Changes

- Add `world/art/connectivity.py`: `probe(*, force=False) -> ProbeResult` —
  one bounded `GET /sdapi/v1/samplers` (the reference's canonical fast probe
  endpoint) through the existing client transport with its own timeout
  (`ART_SD_PROBE_TIMEOUT_MS`, default 5000), returning a structured verdict
  (ok / named error code + host, never credentials) plus a timestamp, and a
  process-local TTL cache (`ART_SD_PROBE_CACHE_SECONDS`, default 300) keyed by
  a **fingerprint of the effective connectivity settings** (base URL, auth
  pair presence, probe timeout) so any operator edit invalidates stale
  verdicts automatically. The probe NEVER raises and NEVER gates generation —
  the worker keeps calling the server regardless (deterministic-playability
  invariant: connectivity is diagnostic, not a permission).
- Add `@art health` (Developer): prints the cached-or-fresh probe verdict
  (`reachable` / named error, with verdict age), the `ART_SCHEDULER_ENABLED`
  state and interval/limit, queue counts per status (pending/in_progress/
  failed/done), and the effective output format/quality/metadata policy — the
  one-screen operator dashboard the reference's settings panel provides.
- Two env-backed settings (typed set 24 → 26): `ART_SD_PROBE_TIMEOUT_MS`
  (integer 1000–60000 inclusive, default 5000) and `ART_SD_PROBE_CACHE_SECONDS`
  (integer 5–3600 inclusive, default 300).

## Capabilities

### New Capabilities
- `art-service-connectivity-surface`: bounded, cached sd-webui reachability
  probing plus the `@art health` operator dashboard (probe verdict, scheduler
  state, queue counts, effective output policy), strictly diagnostic.

### Modified Capabilities
- `art-staff-commands`: `@art health` joins the Developer command surface.
- `settings-environment-overrides`: env-backed set grows from exactly 24 to
  exactly 26.

## Impact

- Code: new `world/art/connectivity.py`; `commands/art.py` (`CmdArtHealth`);
  `server/conf/settings.py` (2 knobs — reuses B's inclusive-bounded integer
  helper); `server/conf/test_settings.py` pop list 26;
  `world/art/tests/test_connectivity.py` (fake transport, fake clock).
- Docs: `.env.example` (2 entries), guide inventory 26 rows + troubleshooting
  row ("probe is diagnostic only; it never blocks generation"),
  `docs/game/commands.md` + `docs/game/command-reference.md` new row/anchor
  (`tests/test_command_docs.py` green).
- No record/schema changes; no worker behavior changes.

## Dependency note

**Must land after `art-output-format-pipeline`** (B), which lands after
`art-generation-config-parity` (A): all three edit the same inventory tables,
`.env.example`, guide, and the same MODIFIED
`settings-environment-overrides` requirement, and `@art health` reports the
format/quality policy B introduces. Apply strictly serially A → B → C.
