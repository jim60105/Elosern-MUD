# Spec Delta

## Purpose

Provide lawful possessed authored conversations with owner-correct relationships through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## ADDED Requirements

### Requirement: Lawful possession can initiate authored dialogue
A lawfully controlled bound companion SHALL initiate and leave authored conversations using its body and portrait. Guild, quest and affinity ownership SHALL remain with the owning player. Invalid possession or self-host contexts SHALL reject before any effect or content delivery.

#### Scenario: Host affinity targets owner
- **WHEN** an elf companion controlled by a human owner selects an authored topic
- **THEN** the companion speaks and host-to-owner affinity changes while host-to-companion affinity does not

#### Scenario: Forged mirror is rejected
- **WHEN** possessed_by names a player but its mirror/session or membership disagrees
- **THEN** no scene, relationship or reading state is produced

### Requirement: Possessed shopping and unrelated restrictions remain unchanged
Enabling authored talk SHALL preserve current possessed trade settlement using the commander purse and named member bag. Existing possession, autonomy and freeform restrictions outside authored talk SHALL remain in force.

#### Scenario: Trade after talk
- **WHEN** a possessed companion leaves a conversation and buys a stocked item
- **THEN** existing lawful trade charges commander copper and adds stock to companion inventory without a new shopping prohibition

#### Scenario: Self-host stays unavailable
- **WHEN** a possessed companion is addressed as the conversation host
- **THEN** existing self-host refusal causes no dialogue or affinity mutation

