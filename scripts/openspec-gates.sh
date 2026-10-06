#!/usr/bin/env zsh
# openspec-gates.sh — project archive gate for the OpenSpec pipeline.
#
# Two phases, split around the OpenSpec CLI sync:
#   archive       PRE-archive, from the feature worktree. Validates the change
#                 and guards already-synced capabilities against regression.
#                 Its traceability read cannot see the change's own new
#                 requirements: those enter the index only after the sync.
#   post-archive  POST-sync, run AFTER `openspec archive <change> --yes` and
#                 BEFORE rebase/merge. This is the AUTHORITATIVE traceability
#                 gate: only here are the change's own requirements present in
#                 `openspec/specs/`, so only here can an uncovered requirement
#                 block the merge.
#
# Contract consumed by os-archive (global worker): run from a feature worktree
# as `scripts/openspec-gates.sh archive <change>`, then, after the CLI archive,
# `scripts/openspec-gates.sh post-archive <change>`. Exit 0 = gate green.
#
# The archive-phase policy for this repo skips the full test suite (user policy;
# CI owns the browser suite and coverage gate). It does NOT skip the two
# correctness gates AGENTS.md makes load-bearing at archive time:
#   1. spec test-traceability: every main requirement has a covering test
#   2. OpenSpec strict validation of every spec/change artifact
#
# Usage: scripts/openspec-gates.sh <phase> [change]   (phase: archive | post-archive)
set -euo pipefail

phase="${1:-}"
change="${2:-}"

case "$phase" in
  archive)
    # PRE-archive. The traceability check is kept as a regression guard for
    # capabilities already synced into openspec/specs/; this change's own new
    # requirements are not yet in the index (see post-archive).
    print -u2 "gate: spec_traceability check"
    uv run --locked python -m tools.spec_traceability check
    print -u2 "gate: openspec validate --all --strict"
    uv run --locked openspec validate --all --strict
    if [[ -n "$change" ]]; then
      print -u2 "gate: openspec validate ${change} --type change --strict"
      uv run --locked openspec validate "${change}" --type change --strict
    fi
    ;;
  post-archive)
    # POST-sync, after the CLI has synced this change's delta specs into
    # openspec/specs/. Authoritative traceability gate: only now are the
    # change's own requirements in the index, so only now can an uncovered
    # requirement be detected before merge.
    if [[ -n "$change" ]]; then
      print -u2 "post-archive gate for change: ${change}"
    fi
    print -u2 "gate: spec_traceability check (post-sync, authoritative)"
    uv run --locked python -m tools.spec_traceability check
    print -u2 "gate: openspec validate --all --strict (post-sync)"
    uv run --locked openspec validate --all --strict
    ;;
  *)
    print -u2 "usage: scripts/openspec-gates.sh <phase> [change]"
    print -u2 "phases: archive (pre-archive) | post-archive (post-sync)"
    exit 64
    ;;
esac
