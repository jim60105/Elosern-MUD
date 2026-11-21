# Spec Delta

## REMOVED Requirements

### Requirement: Optimization is based on reproducible measurements
**Reason**: `docs/` carries no historical profiling reports. Test-suite performance measurement remains a throwaway-script activity governed by `AGENTS.md` and `docs/development/evennia-testing-guide.md`; a committed report is no longer part of the current contract.

**Migration**: Use `git log` and the archived change `2026-08-03-optimize-evennia-testing` for the historical baseline. Delete `docs/development/evennia-test-performance.md` and `TestOptimizationEvidenceTests`; the shard-ownership and fixture-boundary requirements and their tests remain.
