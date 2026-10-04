# Dialogue epoch rendered-budget calibration

Measured offline on 2026-10-04 with the shipped prompt library and `token_est_v3`.
No live model or image service was used. This calibrates the currently supported
local-first profiles, not provider tokenizers or model-quality claims.

| Capability profile | Context window | Completion reservation | Deep Recall | Safety | Maximum input | Summary soft target | Summary hard rendered limit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_dialogue | 16384 | 250 | 512 | 256 | 15366 | 400 | 800 |
| dialogue_summary | 4096 | 1024 | 512 | 256 | 2304 | 400 | 800 |

The npc_dialogue window is sized by the persona-card bounds, not a provider
window: a fully-authored NPC card is capped at 2000 rendered code points
(about 4000 `token_est_v3` tokens) inside the mandatory character anchor, and
the speaking player's public persona block rides the mandatory current frame.
Under the old 4096 window (3078 maximum input) that mandatory floor alone could
exceed the budget with zero history, so every fully-authored card degraded with
`ContextBudgetExceededError`. The dialogue `turn_frames` hard bound is the
maximum input itself: the mandatory current frame lives inside that section, so
a smaller bound could reject after the aggregate reduction loop had already
converged.

Both profiles use the same persisted summary representation. The dedicated
summary output reservation permits a bounded JSON summary, while ordinary
NPC replies keep their existing 250-token completion allowance. Explicit
`max_completion_tokens` overrides replace `max_tokens` for reservation accounting.
Deployment-specific smaller completion budgets additionally bound summary JSON
output; they never weaken the 800-token rendered summary bound.

The synthetic measurement used twelve original-turn records with source IDs,
revision 1, 64-character speech hashes, tick 0, speaker `Synthetic player` and
speech `Can you repair this?`. Their exact sorted JSON plus double-newline
separators measured **1306 estimated tokens**. The shared global rules measured
**106** and the summary instruction **49** before section headings. A recorded
summary, `The player asked about repairs; the NPC offered advice.`, measured
**17** in plain text and **26** as the completion JSON object. Heading and
attribution costs are included by final assembly, not deducted from reservations.

Selection uses a contiguous source prefix of at most twelve original turns and
1800 estimated rendered-frame tokens, below the 2000-token section hard bound.
The unchanged context assembler enforces the final 2304-token input budget,
including headings, global rules, attribution and any prior summary. Provenance
claims only exact source frames actually present in that rendered snapshot.
Summary acceptance measures the epoch-summary heading plus text against 800,
and the completion JSON against the profile completion reservation. A prior
summary generation is referenced only when it was actually supplied.

Oversized or invalid output uses the existing guardrail's bounded retry/degrade
behavior and leaves original turns and the current epoch untouched. Oversized
source turns remain durable and are never sliced into misleading partial
summary sources; compaction can defer while ordinary dialogue uses its bounded
recent view. Historical prompt frames are trimmed oldest-first before optional
current memory/recall, and mandatory current state rejects rather than silently
disappearing. `DialogueEpochTests` exercises accepted, oversized, offline and
stale compaction with recorded responses, exact original provenance, movement
and cache-disabled behavior. These numbers are conservative estimates; provider
reported cached tokens are optional operational metadata only.
