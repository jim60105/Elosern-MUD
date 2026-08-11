## Why

The pre-exam description promises a 「模擬戰」(simulated battle) that restores both sides' HP/MP/SP to full before and after the fight, but the implementation instead runs the exam as nonlethal combat with a session-wide HP floor. This chore aligns the implementation with the documented simulated-battle design: the underlying combat is ordinary lethal combat, and full restoration happens around it.

## What Changes

- The pre-exam description states the exam is a simulated battle and that both sides are restored to full HP/MP/SP before and after.
- Before the exam begins, the candidate's and the examiner's HP, MP, and SP are restored to full.
- Exam combat uses ordinary combat semantics: the examiner follows the normal combat flow until one side's HP reaches 0 (no session-wide nonlethal floor, no special knockout marking).
- After the exam settles, both sides are restored to full HP/MP/SP regardless of outcome; the temporary opponent is deleted as today.
- As a simulation, the fight grants no kill XP/loot and advances no DEFEAT quests or protected-entity failures.

## Capabilities

### Modified Capabilities

- `guild-rank-exams`: examination combat is a simulated lethal battle with pre/post full HP/MP/SP restoration.

## Impact

- `world/rules/combat_session.py` (exam-mode context: remove the nonlethal flag; add restore hooks), `world/rules/guild_exams.py` (pre-restore at start, post-restore at settlement), `commands/combat.py` or exam intro text (simulated-battle description), tests; no changes to ordinary combat mechanics.
