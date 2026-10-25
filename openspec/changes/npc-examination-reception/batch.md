# NPC capabilities and services batch contract

## Approved scope and sequential cutover

The sole scope source is `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md`, committed as aa3dbe64. The request to propose accepts planning; production edits require apply. The project is unreleased. No save migration, old input reader, renamed component alias, profession bundle or new gameplay service is authorized. All artifacts are committed on master with paths limited to their own change directory.

| ID | Change | Direct prerequisites | Tasks | Runnable outcome |
|---|---|---|---:|---|
| R | npc-examination-reception | none | 3 | New reception slot everywhere; qualified adventurers remain separate and have no profession writes |
| H | npc-service-host-identity | R | 4 | Existing canonical profile identity owns reuse and managed reconciliation; live state survives |
| D | npc-direct-capability-declarations | H | 5 | Import/place/roster producers use one direct schema; profession machinery is deleted |
| S | npc-plain-name-presentation | H | 4 | All title readers/composers/editor header fields disappear while remaining creators are still valid |
| N | npc-title-authoring-removal | D, S, authored-dialogue-generated-packages | 4 | All remaining title schemas/validators/writes disappear from final static/generated producers |
| T | npc-targeted-service-flows | R, webclient-settlement-alignment | 5 | Current drawers and six mutation payloads retain an exact provider; rank is independently navigable |
| P | npc-contextual-service-projection | N, D, T, authored-dialogue-generated-packages, authored-dialogue-content-guild | 5 | Derived contextual service descriptors, explicit source associations and real existing route handoffs work in the current flat card |
| X | npc-service-text-parity | P | 4 | Inspection/discovery and explicit provider command suffixes use the same projection/authority |
| U | npc-interaction-service-card | S, P, X, authored-dialogue-reading-client, authored-dialogue-unread-notices, webclient-immutable-adoption | 5 | Production grouped card has fixed common slots, accessible reasons and stale/focus safety |
| G | npc-service-management-inspection | N, P | 4 | Independent GM service descriptions/context-required availability and technical binding/anchor diagnostics |

There are 43 implementation tasks. The direct new-new edges are R->H, H->D, H->S, D->N, S->N, R->T, N->P, D->P, T->P, P->X, S->U, P->U, X->U, N->G and P->G. Other new-new precedence is transitive. A valid implementation sequence, respecting active prerequisite completion, is R, H, D, S, N, T, P, X, U, G. G and X/U can be scheduled independently once their dependencies finish, subject to shared documentation/manifests.

R retains one valid renamed profession expansion mechanism until D removes it. H consumes its resolved plans until D changes inputs; this is sequential replacement of an existing owner, with no added compatibility API. S removes presentation reads before N removes producers. T migrates every current provider action producer/consumer together, so no old payload fallback is needed. P adds working routes to the existing flat card before U changes grouping. X completes text parity without changing services into a new domain implementation. No change ends with an unwired route, fake backend or disabled placeholder for future implementation.

## New-new code-conflict matrix

The table lists all non-manifest overlapping source ownership. Pairs not listed are disjoint in production code and have no extra semantic dependency beyond the graph above. Every pair still serializes shared documentation, `.github/evennia-shards.json`, `.github/browser-shards.json`, showcase ownership and traceability registrations rather than overwriting sibling edits.

| Conflict group | Exact shared source family | New change pairs |
|---|---|---|
| Component vocabulary/config | typeclasses/components.py, profession_config/assembly before deletion, npc_capabilities after cutover, service binding fixtures | R-H, R-D, H-D, D-P |
| Guild deterministic authority | guild_exams.py, human_guild_hosts.py, guild_adventurers.py, guild/registration service gates | R-N, R-T, R-P, R-X, T-X |
| Host and authoring carriers | guild_economy.py, guild_config, settlements/places and shops, imports schema/validate/loader | H-N, D-N, H-S |
| NPC name/identity consumers | typeclasses/npcs.py, npc_identity.py, world/rules/dialogue.py, party_scope, command item messages | S-N, S-P, S-X |
| Current service read/action surfaces | service_view.py, service_actions.py, services serializer/UMD validators and menu builders | R-T, R-S, S-T, T-P, T-U, P-U |
| Dialogue source/selection | common codec/shape, dialogue_sources, dialogue.py, generated package schema | N-P, P-X, P-U |
| Game interaction models | exploration presenter/UMD validator/menu, frame-resolvers, presence.js, use-person-focus, ChoiceCard, AppClient route handoff | S-P, S-U, T-P, T-U, P-U, X-U |
| Independent management | web/gm/readers/npcs.py and GM reader fixtures | R-S, R-G, S-G, N-G, D-G |

Host creation always remains in the deterministic core. Nothing under world/ai applies capability configuration or commerce state. Service opening is navigation/read-only; existing domain owners alone perform registration, trade, exams, enrollment and commission effects.

## Relevant active-change dependency and conflict matrix

All names below were present in `openspec list --json` during planning. Presence in that list is not proof of implementation. Wait for named semantic prerequisites to complete before applying the dependent new slice. Other entries are source integration constraints, not hidden implementation dependencies.

| Active change | New semantic dependency | Actual overlap / integration contract |
|---|---|---|
| authored-dialogue-generated-packages | before N and P | packages.py, generation/prompt, scene_package/compile, dialogue_sources/dialogue.py; N removes title from its final schema, then P adds services associations to the common source-aware format. Preserve topic_effects authority, local/full ID normalization, current phase retirement and immutable package publication |
| authored-dialogue-content-guild | before P | guild_staff.topic_04/report association and guild deterministic report exception; P adds explicit source metadata after the body rewrite, keeping its topic ID and no extra reading/affinity/effect reward |
| authored-dialogue-content-lower-hospitality | none | Existing inn/tavern prose grants no gameplay entitlement. Preserve baseline topics/profile identity; no service inferred from lodging or tavern wording |
| authored-dialogue-content-lower-civic | none | Bathhouse/guardhouse prose is narrative; it does not create a real service |
| authored-dialogue-content-middle-tools | none | Existing merchant components remain trade authority; topic prose does not grant trade |
| authored-dialogue-content-middle-exchange | none | Same profile/topic ownership; merchant-hall prose remains informational |
| authored-dialogue-content-upper-faith | none | ChurchHost enrollment and sanctum merchant stay distinct; no service is inferred from temple faith prose |
| authored-dialogue-content-upper-civic | none | Drill-yard/academy/watch topics promise no training/exam/guard service backend |
| authored-dialogue-content-ciaran-commons | none | Homes/dialogue remain narrative; no automatic attendant service |
| authored-dialogue-content-ciaran-crafts | none | Shipped merchant functionality remains owned by direct Merchant declarations |
| authored-dialogue-content-ciaran-fare | none | Shipped merchant functionality remains; no prose/service inference |
| authored-dialogue-refresh-lifecycle | none, serialize shared writers with R/H/S/T/P | guild.py/exams, NPC move/delete hooks and possession/time callbacks; retain post-commit owner discovery, old-context retirement and current actor re-resolution. New provider navigation does not replace these refresh owners |
| authored-dialogue-reading-client | before U | dialogue_reading.js, transport, dialogue-view, AppClient and return-to-choices; service/opening/refusal deliveries create no formal reading receipt and no optimistic eligibility |
| authored-dialogue-unread-notices | before U | dialogue.py, availability, pushes, reading client/toasts/DialogueChoices; preserve dedup, deferral and non-focus-stealing notices when services open/close |
| webclient-delta-contract | transitive before T through settlement-alignment | protocol metadata/constants/fixtures; preserve exact-base E/R/B, removed_panels and staged mode/dialogue checks; panel schema changes do not alter envelope semantics |
| webclient-publication-baseline | transitive before T | coordinator/dispatcher/ingress/current push candidates; services.open read results remain private and target-correlated; provider mutations use existing canonical publication helpers |
| webclient-publication-settlements | transitive before T | causal callback groups and NPC cleanup; H rollback and U departure do not bypass after-commit boundaries or retain causal tokens |
| webclient-publication-codec | no additional dependency, serialize protocol/constants fixtures | Keep panel-local bounds and general publication preflight. No new transport protocol or relaxed envelope limit |
| webclient-publication-assembly | no additional dependency, serialize receiver fixtures | Do not expose incomplete service panels or adopt metadata before multipart completion |
| webclient-sync-recovery | transitive before U through immutable-adoption | transport/generation/result gate; service responses from obsolete transport/card are discarded and no local retry grants gameplay authority |
| webclient-movement-alignment | transitive before T through settlement-alignment | relocation identity/causal settlement; reused-host sync no longer relocates NPCs. Real movement/departure keeps existing committed lifecycle publication |
| webclient-settlement-alignment | before T | service_actions exam start/terminal receipt classification; preserve committed checkpoint facts and schedule-only no-mutation result |
| webclient-immutable-adoption | before U | presence/interaction/hud/view/frame resolvers; store rendered mapping signatures and origin focus only in client-owned mutable state, never decorate frozen panels or reset on same-content alignment |
| webclient-sync-functional-smoke | no additional dependency, serialize browser fixtures/manifests | Keep its large-publication/recovery smoke ownership; U adds a separate focused real NPC shop/reception smoke and does not replace full synchronization acceptance |

## Active proposal amendment contract

The planning assignment limits commits to each new `openspec/changes/<change>/` directory. Existing active proposal files and production/current main specs are therefore intentionally unchanged during this planning run. This batch artifact supplies their explicit supersession context now; the following exact amendments are part of the owning apply tasks, not extra discovery work. Archived changes and the approved source document are never edited.

| Owner | Still-active targets | Concrete amendment text to add to design/proposal/tasks and materially affected current deltas at apply |
|---|---|---|
| N | authored-dialogue-generated-packages | `NPC characterization excludes title. Require display_name/persona and retain role/tier, age pair, portrait, canonical identity/digest and generated package authority; no title field is accepted, serialized, prompted or written. Apply title removal after generated-packages, before contextual service projection.` |
| N | all ten authored-dialogue-content-* names enumerated above | `Host functionality uses explicit capabilities and canonical profile identity, with no profession or independent NPC title field. Keep authored narrative voice/roles inside existing persona/description/dialogue prose and preserve topic IDs; prose never grants a service.` No baseline body rewrite is requested by this amendment |
| P | authored-dialogue-generated-packages | `The optional services association list uses exact key/topic_id/label rows, same-source/same-phase canonical topic IDs and existing deterministic supported effects only. It grants no effect, reading completion or additional authority at projection/open time; invalid associations reject the complete source/package.` |
| P | authored-dialogue-content-guild | `Keep guild_staff.topic_04 as the deterministic report/list entry. Declare the explicit guild_report_dialogue association after content authoring; the association grants no registration, turn-in reward or formal reading completion.` |
| T | webclient-settlement-alignment | `Provider-dependent service actions carry required npc_id, resolve that exact provider and preserve existing start/terminal/schedule-only causal settlement classification. services.open is a private read and never an examination start or mutation.` |
| U | authored-dialogue-reading-client, authored-dialogue-unread-notices, webclient-immutable-adoption | `NPC service navigation preserves source-aware reading receipts/contexts, ignores opening/service/refusal completion, defers notices without focus theft and keeps menu signatures/focus origins outside immutable committed presentation. Late provider responses cannot reopen retired cards.` |

Remaining active publication/lifecycle changes require integration preservation only; no planned behavior or delta requirement is superseded. Do not mark them completed, rewrite their authorship, or invent semantic dependencies to avoid ordinary shared-file coordination.

## Coverage of approved acceptance

| Approved design sections | Complete owners and permanent evidence |
|---|---|
| 4.1, 4.2 direct input, mixed binding, atomicity | D validates exact schema/types/kwargs/references/anchors, import/roster use one core; invalid last row and faulted add/update/remove roll back database plus handler caches |
| 4.3 host identity and reconciliation | H tests canonical identity through reorder/add/remove/empty plan, duplicate ownership rejection and unchanged stock/restock/location/inventory/relationships; whole-row lifecycle remains separate |
| 5 examination and unused profession | R tests reception vs qualification and no adventurer profession writes; T preserves target reception plus independently selected actual adventurer and schedule-first existing eligibility |
| 6 identity and companions | S removes every identity reader/composer; N removes all producer fields/writes. Player title and scene role/tier/name/age/portrait behavior remain; no service capability changes current recruitment or possession eligibility |
| 7 contextual services | T explicit provider read/action cutover; P exhaustive real-service mapping and explicit source associations, with hidden/locked/phase/stale validation and no prose inference |
| 8.1 numbering and mapping | U fixed talk/look, conditional order, service order, paused positions, digits only 1..9 and fresh selection after mapping changes |
| 8.2 states | P/U none vs unreadable, zero stale service rows, disabled reasons and departure closure |
| 8.3 inputs and focus | U real labeled groups, focusable disabled rows, pointer/keyboard Home/End/Enter/Space/Escape, service return and rail fallback. X text discovery/targeting parity updates both references |
| 9 management | G existing GM primitives with context-required availability and complete configuration diagnostics; no impersonation or game Vue imports |
| 10 cutover/docs | Every owner changes current deltas/docs/tests/callers and removes its obsolete APIs; N/P/T/U amend materially affected still-active artifacts as above. No history rewrite, compatibility shim or data migration |
| 11 prototype limitations | U accessible real headings replace CSS-only output. No prototype control strip enters production. Existing backend flows are exercised, and synthetic overflow remains explicitly test-only |
| 12 verification | Each owner has focused commands; new tests are named as proposed additions. U runs actual production merchant purchase and reception route smoke with AI disabled. Final implementation contract gate, shard ownership and relevant logging checks are required; full browser/evidence suites stay CI-owned |

## Proposal verification record

Final strict validation, phase output and independent critique disposition are reported by the planning handoff. No gameplay test/build/lint/formatter or prototype rebuild is claimed by proposal creation. Each proposal's unchecked tasks are intended implementation work, never evidence that implementation occurred.
