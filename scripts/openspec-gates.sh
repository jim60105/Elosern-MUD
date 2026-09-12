#!/usr/bin/env zsh
# openspec-gates.sh — project archive gate for the OpenSpec pipeline.
#
# Contract consumed by os-archive (global worker): run from a feature worktree
# as `scripts/openspec-gates.sh archive <change>`. Exit 0 = gate green.
#
# The archive-phase policy for this repo skips the full test suite (user policy;
# CI owns the browser suite and coverage gate). It does NOT skip the two
# correctness gates AGENTS.md makes load-bearing at archive time:
#   1. spec test-traceability: every main requirement has a covering test
#   2. OpenSpec strict validation of every spec/change artifact
#
# Usage: scripts/openspec-gates.sh <phase> [change]   (phase: archive)
set -euo pipefail

phase="${1:-}"
change="${2:-}"

case "$phase" in
  archive)
    print -u2 "gate: spec_traceability check"
    uv run --locked python -m tools.spec_traceability check
    print -u2 "gate: openspec validate --all --strict"
    uv run --locked openspec validate --all --strict
    if [[ -n "$change" ]]; then
      print -u2 "gate: openspec validate ${change} --strict"
      uv run --locked openspec validate "${change}" --strict
    fi
    ;;
  *)
    print -u2 "usage: scripts/openspec-gates.sh archive [change]"
    exit 64
    ;;
esac
