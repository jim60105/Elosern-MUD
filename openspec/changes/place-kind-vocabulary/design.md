## Context

`PlaceKind` was written alongside the first six places and fitted them exactly. The settlement build adds eighteen more, of which roughly a dozen have no honest value in the enum.

The field has no reader. Grep finds `place.kind` used nowhere in `world/rules/`, `world/maps/` or `commands/` — only in the registry modules that author it. So a wrong value is inert, which is precisely the danger: nothing fails, and the registry quietly fills with locations that misdescribe themselves.

## Goals / Non-Goals

**Goals.** A vocabulary that covers what is being built. A stated rule for what a kind means, so the next author does not have to infer it.

**Non-Goals.** No reader. `kind` stays descriptive metadata; this change does not give anything permission to branch on it, and a runtime gate reading `kind` would be the same mistake `professions.yaml` warns about for professions.

## Decisions

### A kind describes the location, not the host

This is the rule the existing data already follows without saying so. The four elven homes are `HOME`, though every one of them sells something — a `WEAPONSMITH` value was available for 海莉爾 and was not used. That is correct and it is the whole distinction: in the village, a blade-maker's dwelling is a dwelling, and the fact that you can buy a blade there is a property of who lives in it.

Writing the rule down makes `HOME` for a trading elf read as deliberate rather than as an oversight, and tells the author of the next settlement which axis to classify on.

It also settles the awkward cases in advance. The sanctum shop is `SANCTUM_SHOP` rather than `GENERAL_STORE` because what it is, is the counter attached to a temple. The market stalls are `MARKET` even though nobody staffs them, because the kind describes the ground, not the staffing.

### Fourteen members, not a generic escape hatch

The alternative is one `OTHER` or `LANDMARK` value absorbing everything that does not fit. Rejected: a catch-all member is a vocabulary that has given up, and it would put a palace, a bathhouse and a drill yard in one bucket whose only shared property is that nobody named them.

Fourteen is a lot of members for an enum nothing reads, and that is acceptable — the cost is one line each, and the benefit is that the registry describes the world accurately for whatever eventually does read it.

### The vocabulary lands before the content, in its own change

Every content change needs values that do not exist yet. Extending the enum inside one of them would make the other five depend on it for a reason unrelated to what that change is about, and extending it piecemeal — each change adding the two members it needs — would produce a vocabulary designed by accretion, which is how it got outgrown the first time.

## Risks

**Some members will go unused if a location is later cut.** Cheap to remove, and an unused member is a smaller problem than a missing one.

**The rule may be read as licence to branch on `kind`.** The design says explicitly it is not. If a mechanism ever needs to distinguish location types at runtime, that is a separate decision with its own change, and it should be scrutinised the way profession-as-runtime-lens already is.
