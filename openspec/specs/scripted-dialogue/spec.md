# scripted-dialogue Specification

## Purpose

Let service NPCs (such as guild staff) answer authored `talk` lines in
character, explaining their place in in-world terms without naming commands or
game mechanics, through a generic, immutable, keyed dialogue mechanism that
causes no state change.

## Requirements

### Requirement: Scripted dialogue hosts answer authored talk lines

An NPC carrying a `ScriptedDialogue` component SHALL answer known keywords with
the authored response and unknown keywords with the no-understanding line, where the
no-understanding line SHALL be the misunderstanding reply authored by the NPC profile named in the
host's persona provenance when that profile authors one, and the shared no-understanding line
otherwise (no profile provenance, or a profile without a misunderstanding reply); a provenance
profile key that does not resolve SHALL emit an operational integrity error naming the NPC and key
and SHALL use the shared line, never a fabricated personalized line. Editing the host's runtime card
SHALL NOT change any authored greeting, response, or misunderstanding reply,
without causing state change except that a known-keyword answer SHALL grant +1 affinity
(`talk` source) with the host through the sole-writer affinity API (`world/rules/affinity.py`),
applied by the deterministic talk writer in the same transaction as the answer; unknown keywords
and no-keyword paths SHALL NOT write any state.
`talk <npc>` without a keyword SHALL present the NPC's own non-empty offline-greeting field first,
then the host's authored table greeting when one is configured, then the greeting authored by
the profile named in its persona provenance, and the no-response line only when every applicable
source is absent. The instance override SHALL display literally at the text-output boundary;
trusted authored defaults SHALL retain their existing formatting. A known-keyword response and
the no-understanding line SHALL NEVER consult the offline-greeting field. An NPC without any
dialogue component SHALL use the same instance-then-profile greeting precedence on the no-keyword
path and SHALL yield no-response only when both are absent; this SHALL NOT add keyword
conversation capability to a componentless NPC. The
`guild_staff` host SHALL be the dialogue action exception: the keyword `回報`
SHALL resolve the read-only reportable-quest listing through the deterministic
guild service without granting the talk affinity, and `talk <guild-staff> 回報 <quest_id>` SHALL
turn in exactly that quest through `turn_in_quest` with the same atomic exactly-once
settlement and rejection semantics as `guild turnin`. Every other `guild_staff`
keyword SHALL grant the same +1 affinity as any other known-keyword answer.
Before answering, the scripted-talk entry path SHALL consult
`world/rules/npc_schedules.py::interaction_reason(npc, "talk")`; a non-`None` result SHALL present
that stable rejection line and SHALL write no state — the +1 affinity and
turn-in paths are both bypassed for the blocked interaction.

#### Scenario: Guild staff answers a known keyword
- **WHEN** the player talks to the guild master with a keyword such as 公會 or 任務
- **THEN** the guild master answers with the authored response for that keyword, the host's
  affinity value rises by 1, and no other state changes

#### Scenario: No-keyword talk presents the host's greeting
- **WHEN** the player runs `talk <guild-master>` without a keyword
- **THEN** the guild master presents its authored greeting teaching the guild
  commands, and no state changes (including no affinity change)

#### Scenario: An author-set offline greeting overrides the table greeting
- **WHEN** an author has saved a non-empty offline-greeting field on a table-backed host and the player runs `talk <host>` without a keyword
- **THEN** the host presents the field's text literally instead of its table greeting, and a known-keyword answer is still the authored table response

#### Scenario: Missing greeting falls back to the no-response line
- **WHEN** the player runs `talk <scripted-host>` without a keyword, the host
  has no table or profile greeting, and its offline-greeting field is empty
- **THEN** the player receives the no-response line and no state changes

#### Scenario: Unknown keyword yields the no-understanding line
- **WHEN** the player talks to a scripted dialogue host with an unrecognized
  keyword
- **THEN** the host gives the no-understanding line and no state changes

#### Scenario: Componentless NPC still yields no response
- **WHEN** the player talks without a keyword to an NPC that carries no dialogue component,
  has an empty offline-greeting field, and has no applicable authored profile greeting
- **THEN** the player receives the no-response line and no state changes

#### Scenario: Clearing a componentless override restores the profile greeting
- **WHEN** the player clears a componentless NPC's offline-greeting override and then talks
  without a keyword to that NPC whose profile authors a greeting
- **THEN** the authored profile greeting is presented with its trusted formatting and no talk state changes

#### Scenario: Guild staff 回報 keyword lists reportable quests read-only
- **WHEN** a registered player with completed, unclaimed quests talks to the
  guild staff with the keyword `回報` and no quest id
- **THEN** the staff answers with the deterministic reportable-quest listing in
  `(accepted_tick, quest_id)` order and no quest, wallet, inventory, merit, or
  claim state changes

#### Scenario: Guild staff 回報 with a quest id turns the quest in
- **WHEN** the player talks to the guild staff with `回報 <quest_id>` naming a
  reportable quest
- **THEN** the staff turns the quest in through `turn_in_quest`, paying the
  exact reward once and answering with the same success or rejection prose as
  `guild turnin`

#### Scenario: Guild staff 回報 without a reportable quest says so
- **WHEN** a registered player with no completed-and-unclaimed quests talks to
  the guild staff with the keyword `回報`
- **THEN** the staff answers that there is nothing to report and no state
  changes

#### Scenario: Unregistered player asking 回報 gets guidance, no state change
- **WHEN** a player without a guild registration talks to the guild staff with
  the keyword `回報`
- **THEN** the staff answers with the authored register-first guidance and no
  quest, wallet, inventory, merit, or claim state changes

#### Scenario: 回報 on a non-guild host stays a plain unknown keyword
- **WHEN** the player talks to any dialogue host other than the `guild_staff`
  host with the keyword `回報`
- **THEN** the host gives the no-understanding line and no state changes

#### Scenario: A schedule-blocked host does not answer and writes nothing
- **WHEN** the player talks to a scripted dialogue host whose schedule state blocks `talk`
- **THEN** the player receives the stable schedule rejection line, and no affinity
  or turn-in state changes

#### Scenario: A profiled host misunderstands in its own voice
- **WHEN** the player talks with an unknown keyword to a scripted host whose persona provenance names a profile authoring a misunderstanding reply
- **THEN** the host answers with that profile's misunderstanding reply verbatim, no LLM is consulted, and no state changes

#### Scenario: A dangling profile reference is an integrity failure
- **WHEN** a scripted host's persona provenance names a profile key absent from the profile registry and the player uses an unknown keyword
- **THEN** an integrity error event names the NPC and the key, the shared no-understanding line is returned, and no state changes

#### Scenario: Card edits do not rewrite scripted lines
- **WHEN** a profiled scripted host's runtime card is edited and the player then uses a known keyword, no keyword, and an unknown keyword
- **THEN** the authored response, table greeting, and profile misunderstanding reply are returned unchanged

### Requirement: Editable offline greeting text is literal at every speech output boundary
A non-empty per-instance offline greeting SHALL be plain text on all no-keyword and degraded speech surfaces: scripted and componentless text commands, browser conversation-open narrative/action messages, and degraded generative-NPC speech. Its literal tokens, including color, newline and MXP command/URL markers and repeated pipes, SHALL NOT create formatting, extra lines or interactive links. Escaping SHALL occur only for the text-output surface, exactly once; storage, private editor fields, dialogue-session/OOB lines and settled-line observer values SHALL retain the normalized raw text. An editable override SHALL remain literal even if its text equals an authored default. Clearing the override SHALL restore the trusted authored table/profile default with its existing formatting. Known keywords and misunderstanding replies SHALL remain authored-only.

#### Scenario: Markup-like override displays as literal speech
- **WHEN** an author saves a valid greeting containing `|/`, `|r`, repeated pipes, an MXP command link and an MXP URL link, then uses each no-keyword or degraded speech surface
- **THEN** the displayed override contains those literal tokens with no token-induced linebreak, color or actionable link and all raw storage/session/editor values remain unchanged

#### Scenario: A degraded reply retains raw observer state
- **WHEN** generative dialogue degrades for an NPC with an editable markup-like greeting and its existing completion gates pass
- **THEN** speech is literal, the settled dialogue observer receives raw text, and persona/version, affinity and intents are unaffected by escaping

#### Scenario: Matching default text does not grant formatting trust
- **WHEN** an editable greeting equals a trusted default containing a color token
- **THEN** the override displays that token literally, but clearing the field restores the authored default's normal color behavior

#### Scenario: Browser republishing does not double escape
- **WHEN** conversation-open stores a markup-like override and the dialogue panel is refreshed or restored after reconnect
- **THEN** the raw OOB line displays as literal text without adding extra escape characters or interactive markup

### Requirement: Dialogue tables are immutable, keyed, and registry-backed
The dialogue-table registry SHALL be keyed by `dialogue_key` and SHALL hold only
frozen `DialogueDefinition` values composed of an optional `greeting` and a
tuple of frozen `KeywordResponse` values. The registry SHALL be read-only at
runtime. A `dialogue_key` with no registered table SHALL resolve to the
no-understanding line for keywords and to no greeting. The `guild_staff`
definition SHALL include the `回報` keyword, whose authored response serves as
the register-first fallback for unregistered players. The `guild_staff` greeting
and keyword responses SHALL be spoken in character: they SHALL tell, in the
host's own in-world voice, what the guild counter is for (registering as an
adventurer, taking commissions from the board, reporting finished work back at
the counter with the commission's number, giving up a commission, and asking
where one stands in rank), and SHALL NOT name a command, a game mechanic, or an
interface element. Command discoverability belongs to help, documentation and
the interface.

#### Scenario: guild_staff definition registers and answers command guidance
- **WHEN** the `guild_staff` dialogue definition is registered and queried
- **THEN** its greeting and keyword responses describe registering, taking a
  commission from the board and reporting it back at the counter, and none of
  them contains a backticked token or a `guild` command name

#### Scenario: guild_staff definition carries the 回報 keyword for chip rendering
- **WHEN** the `guild_staff` dialogue table is inspected for keyword chips
- **THEN** it exposes the `回報` keyword alongside the authored service
  keywords, bounded by the existing keyword limit

#### Scenario: A missing table yields the no-understanding line
- **WHEN** a dialogue lookup references a `dialogue_key` absent from the registry
- **THEN** the no-understanding line is returned for keywords and no greeting is
  resolved, and nothing is written
