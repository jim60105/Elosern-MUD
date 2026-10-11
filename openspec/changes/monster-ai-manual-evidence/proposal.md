# Proposal

## Why

Provide isolated manual encounter, paired-selector and whole-policy performance evidence outside default tests. This is a bounded part of the approved monster combat AI roadmap, not a claim that configuration alone completes attack behavior.

## What Changes

- Manual acceptance SHALL use six archetypes, six synthetic situations, two documented seeds and intelligence 10/90, totaling 24 encounters per archetype and 144 utility encounters. Intelligence SHALL be the only paired variant difference. Encounters SHALL use real production settlement and committed reload.
- A standalone manual selector check SHALL compare exactly two legal candidates with utility gap 0.5 using the same 128 documented injected seeds at intelligence 10/90. High-intelligence highest-utility frequency SHALL exceed low by at least 15 percentage points. Counts, paired difference and Wilson intervals SHALL be reported.
- Manual performance SHALL time snapshot, legality, estimation, scoring, sampling and configured trace overhead using monotonic wall clock and actual ORM queries. The reference envelope SHALL use 16 live participants, up to 16 owned active skills and 256 candidate budget. Warm utility p95 SHALL be at most 50 ms on the recorded host.
- Reports SHALL provide machine-readable JSON and compact Markdown interpretation with baseline commit, algorithm/config fingerprints, versions, host/clock, scenarios, seeds, initial memory, intelligence, raw paired results, approximation flags, omissions and unresolved outcomes. Detailed traces SHALL be opt-in and exclude hidden intent.
- Manual selector, one named archetype and performance operations SHALL be explicit and independent. They SHALL NOT execute in startup, default test discovery, CI or contract gates. Ordinary and overwhelm production smoke SHALL separately verify real context and internal round/slot identity.

## Capabilities

### New Capabilities

- `monster-ai-manual-validation`: Provide isolated manual encounter, paired-selector and whole-policy performance evidence outside default tests.

### Modified Capabilities

None.

## Impact

Approved simulation design replaces the original large campaign with 144 encounters and 128 paired selector seeds. The repository uses uv-managed Django/Evennia setup, synthetic fixtures and explicit shard ownership. No manual campaign belongs in full-suite discovery or contract_gate. Implementation must update AI authoring/development documentation and the release changelog. Player command documentation remains unchanged because no command is added. No new service, package dependency, persistent AI schema or compatibility layer is authorized.

## Batch:

```text
depends-on: monster-ai-observed-coordination
```

Code-conflict notes. Shares manual operations/report fixtures and documentation with staged activation; activation consumes these reports and must not run the campaign through ordinary gates. Shared shard manifests and release notes require integration in dependency order.

Downstream apply uses `feat/monster-ai-manual-evidence` and `.worktrees/monster-ai-manual-evidence`; proposal artifacts are committed on master and this planning operation creates neither.
