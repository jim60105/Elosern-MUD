# openspec-cli-version-pinning Specification

## Purpose

This capability pins the OpenSpec CLI version that the repository's quality gate installs and validates with, so strict OpenSpec validation always runs under the version the project has standardized on, and a committed contract test keeps the CI install command from drifting away from it.

## Requirements

### Requirement: The quality-gate workflow installs the pinned OpenSpec CLI version

The quality-gate workflow SHALL install the OpenSpec CLI as `@fission-ai/openspec` at the project-standardized version `1.13.0`, expressed as a literal version pin in the "Install OpenSpec" step's npm install command. A committed assertion in the existing workflow contract test SHALL pin that step's `run` text to the exact install command, so any edit changing the installed version fails the top-level test suite. The test MUST NOT invoke the network or the `openspec` binary.

#### Scenario: CI installs and validates with the pinned version

- **WHEN** the preflight job runs its OpenSpec install step followed by the strict validation step
- **THEN** the install step runs exactly `npm install --global @fission-ai/openspec@1.13.0`
- **AND** `openspec validate --all --strict` runs under that installed version

#### Scenario: Editing the install step away from the pinned version fails the contract test

- **WHEN** the "Install OpenSpec" step's `run` text in the quality workflow is edited to install any version other than `@fission-ai/openspec@1.13.0`
- **THEN** the top-level workflow contract test fails and identifies the install step
