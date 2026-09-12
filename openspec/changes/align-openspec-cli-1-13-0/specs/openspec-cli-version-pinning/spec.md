# openspec-cli-version-pinning Specification (delta)

## Purpose

This capability pins one authoritative OpenSpec CLI version for the repository and makes every validation entry point — the CI preflight install step and the project archive gate script — resolve and verify that exact version, so strict OpenSpec validation always runs under the version the project has standardized on and version drift fails loudly instead of silently disagreeing.

## ADDED Requirements

### Requirement: The repository declares one authoritative OpenSpec CLI version

The repository SHALL carry a single authoritative OpenSpec CLI version declaration in `openspec/CLI_VERSION`, containing only a semantic version (`MAJOR.MINOR.PATCH`) followed by a newline. Every validation entry point MUST obtain the CLI version it installs or asserts from that file rather than repeating a literal version string, and the declared version at the time of this change is `1.13.0`.

#### Scenario: CI installs the CLI at the declared version

- **WHEN** the preflight job runs its OpenSpec install step
- **THEN** the step's npm install command interpolates the version from `openspec/CLI_VERSION` rather than a literal pin
- **AND** the installed CLI reports exactly the declared version

#### Scenario: A version bump touches only the pin and the test's expected literal

- **WHEN** a maintainer updates `openspec/CLI_VERSION` to a new release and updates the contract test's expected version literal to match
- **THEN** the CI install step and the archive gate assertion both act on the new version with no other file edited, and no file embeds the old version as an install pin

### Requirement: The archive gate fails when the CLI version does not match the pin

`scripts/openspec-gates.sh` SHALL verify, before running any OpenSpec validation gate, that the `openspec` binary it is about to invoke reports exactly the version declared in `openspec/CLI_VERSION`. On mismatch the script MUST exit non-zero and print a message naming both the detected and the declared version, and it MUST NOT run any `openspec validate` command. On match it SHALL invoke `openspec validate` directly, without a `uv run` wrapper, while Python-side gates continue to run through `uv run --locked`.

#### Scenario: Mismatched CLI blocks the archive gate

- **WHEN** the archive gate script runs with an `openspec` on `PATH` whose reported version differs from `openspec/CLI_VERSION`
- **THEN** the script exits non-zero, names the detected and declared versions, and runs no validation command

#### Scenario: Matching CLI passes the archive gate

- **WHEN** the archive gate script runs with an `openspec` reporting exactly the declared version
- **THEN** the script proceeds to run `openspec validate --all --strict` and the remaining archive gates

### Requirement: A committed contract test detects CLI pin drift

The repository SHALL carry a top-level contract test, discovered by the existing top-level test entry point without any shard-manifest change, that reads only committed files and asserts that: `openspec/CLI_VERSION` is well-formed semantic version text equal to the version the project standardizes on; the workflow's OpenSpec install step derives its version from `openspec/CLI_VERSION` and embeds no other literal CLI version pin; and `scripts/openspec-gates.sh` contains a version assertion referencing `openspec/CLI_VERSION`. The test MUST NOT invoke the network or the `openspec` binary.

#### Scenario: Editing the workflow install step to a literal version fails the contract test

- **WHEN** the OpenSpec install step in the quality workflow is edited to hard-code a CLI version instead of deriving it from `openspec/CLI_VERSION`
- **THEN** the top-level contract test fails and identifies the workflow install step

#### Scenario: Removing the gate-script assertion fails the contract test

- **WHEN** the version assertion referencing `openspec/CLI_VERSION` is removed from `scripts/openspec-gates.sh`
- **THEN** the top-level contract test fails and identifies the gate script
