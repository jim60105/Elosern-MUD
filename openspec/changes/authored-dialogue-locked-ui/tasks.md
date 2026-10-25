# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Locked row presentation

- [ ] 1.1 Map server availability/action descriptors into ChoiceCard with selectable lock glyph and aria-describedby hover/focus hint. Add synthetic Vitest tests distinguishing locked-refusal from disabled in-flight; document this distinction in component contract comments.

## 2. Playback and focus refresh

- [ ] 2.1 Keep refusal completion local and formal-only completion event separate, preserve stable-ID focus through changed rows and allow scrolling every declared topic. Add DialogueChoices/AppClient tests for hidden absence, long hint, >4 topics and no portrait switch on refresh.

## 3. Browser and showcase acceptance

- [ ] 3.1 Add one focused locked-refusal/hint browser method and Storybook fixture, register ownership and check app-shell.css duplicate overrides. Verify focused Vitest/browser acceptance and contract_gate without implementing reading persistence.

