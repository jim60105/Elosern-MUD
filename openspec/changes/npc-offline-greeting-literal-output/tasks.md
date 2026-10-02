## 1. Resolve source without modifying canonical text

- [ ] 1.1 Replace the string-only greeting resolver with one minimal raw-text/source-distinguished result, migrate every consumer and remove obsolete resolver references; verify override/default/absent precedence including override identical to its formatted default and companion preset-seeded editable fields.
- [ ] 1.2 Apply literal Evennia escaping only when composing both command no-keyword branches, talk-open narrative/result messages and degraded NPC speech; verify trusted default/usage formatting remains unchanged and no normalizer, global raw switch or stored escaping is introduced.

## 2. Consumer-visible regression coverage

- [ ] 2.1 Add focused regressions exercising the real ANSI/MXP parser with synthetic `|/`, color, command-link, URL-link and repeated-pipe overrides through all four consumer rows in design.md; verify literal rendered text/no links and clearing restores actual trusted formatting rather than asserting helper calls.
- [ ] 2.2 Verify editor read/update data, canonical storage, dialogue-session/OOB line and degraded settled-line callback retain raw text, without version/state change caused by output escaping; preserve stale-persona, schedule and visibility gates and authored keyword responses.
- [ ] 2.3 Audit browser dialogue/editor/narrative rendering of raw versus Evennia-escaped slots and adjust only an actual markup-interpreting consumer; verify refreshed/reconnected panels show single literal tokens, no double escaping, and no hidden card data leaks.

## 3. Future smoke and documentation

- [ ] 3.1 Run focused dialogue/command/NPC/action/frontend consumer tests after integration; register any new test only through its owning shard and data-freeze conventions and remove obsolete incidental wording assertions.
- [ ] 3.2 Save a synthetic markup-like greeting through an actual ordinary-account editor, exercise no-keyword command, browser conversation-open and an intentionally unavailable dialogue client, then clear and repeat; inspect actual narrative/dialogue output and reconnect for literal/no-link/default-format evidence without a live model requirement.
- [ ] 3.3 Update greeting-authoring/output documentation and changelog, retaining the 300-code-point rule and narrow public-speech privacy exception; verify strict OpenSpec validation and traceability. These tests/smokes are future implementation tasks, not executed while proposing.
