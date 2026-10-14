# Spec Delta

## Purpose

Define consistent real-portrait face cropping and Unicode name initials for every avatar through shared load state and accessible local failure presentation.

## ADDED Requirements

### Requirement: Every avatar uses a real portrait or a grapheme initial
Avatars SHALL try their subject's real-image attempts and use geometry from the successful image. Otherwise they SHALL display the first Unicode grapheme cluster of the trimmed displayed name, or a neutral symbol for an empty name. Avatars SHALL never request figure silhouettes or change generation state.

#### Scenario: Unicode names remain intact
- **WHEN** names begin with a combining sequence, astral character or ZWJ emoji after whitespace
- **THEN** the displayed initial is one complete grapheme without isolated surrogates

#### Scenario: Missing avatar is expected
- **WHEN** an avatar has no generated record or optional art
- **THEN** its name initial appears without an error indication or silhouette request

#### Scenario: Fallback geometry belongs to its actual image
- **WHEN** the first portrait fails and a later image with different face geometry succeeds
- **THEN** the avatar uses the later image's rectangle and retains the reached failure marker

### Requirement: Compact avatar failures remain accessible
Roster, presence, party and participant avatars SHALL consume the common load state and retain reached failures after fallback. Compact indications SHALL have keyboard-usable explanations and assistive text without hover-only or color-only meaning.

#### Scenario: Fallback initial retains an error
- **WHEN** a real avatar request fails and no other real image succeeds
- **THEN** the initial remains with a persistent keyboard-accessible failure explanation

#### Scenario: Surface parity holds
- **WHEN** the same descriptor is rendered in switcher, rail, party and participant surfaces
- **THEN** source order, generation truth and reached-fault behavior match without local URL caches

