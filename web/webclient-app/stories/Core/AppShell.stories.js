import { createApp, h, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { createPinia, disposePinia } from "pinia";
import AppShell from "../../components/AppShell.vue";
import AppClient from "../../AppClient.vue";
import { useElosernStore } from "../../stores/elosern.js";
import { createWindowBridge } from "../../bridge.js";
import CombatMenu from "../../lib/combat_menu.js";
import * as protocolFixtures from "../../tests/store/protocol_fixtures.js";
import { COMPANION_PORTRAIT_CATALOG, PARTY_PANEL_FULL_SAMPLE } from "../fixtures/party_panels.js";
import {
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
  COMMAND_HISTORY_SAMPLE,
  FOE_PORTRAIT_CATALOG,
  PARTY_PARTICIPANTS,
  combatSkills,
  foeParticipants,
  withPlateConditions,
  NARRATIVE_SAMPLE,
  OBJECTIVES_PANEL_SAMPLE,
  PARTY_PANEL_SAMPLE,
  PROMPT_SAMPLE,
  STATUS_SLICE_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  STAGE_JOURNEY_STOPS,
  SCENE_SUBJECT,
  fixtureDigest,
  sceneBlock,
  sceneDescriptor,
  sceneResource,
  stageJourneyLocalMap,
  stageJourneyScene,
} from "../fixtures.js";

// AppShell (root/layout). Passive B1 contract: renders the slices it is
// given and emits user intent; the primary states are the transport
// connection states the shell is rendered in offline.
//
// Props: mode (contextual mode slice, rendered as data-elosern-mode),
// connected / locationLabel / timeLabel (TopBar slice), narrative (log
// slice), connectionStatus ("connecting" | "waiting" | "offline" | "ready"),
// offline (offline-overlay slice), prompt, commandHistory (drawer slices).
// Events: submit-command(text) — one deliberate send from the drawer.
//
// Shell key contract: `/` or the ⌨ toggle expands the collapsed command line
// and focuses `#inputfield` (slash stays literal text inside editables);
// Escape or an accepted send collapses the line and returns focus to
// `#action-dock`. The mount retires the replaced text fallback
// (hidden, not removed).

let mountedShell = null;
const renderShell = (args) => ({
  setup() {
    const shell = ref(null);
    onMounted(() => {
      mountedShell = shell.value;
      if (shell.value?.$el) {
        shell.value.$el.__elosernShell = shell.value;
      }
    });
    return () => h(AppShell, { ...args, ref: shell });
  },
});

export default {
  title: "Core/AppShell",
  component: AppShell,
  parameters: {
    docs: {
      description: {
        component:
          "The offline desktop shell composing TopBar, MessageWindow, " +
          "the 日誌 log control, the ⌨ command-line toggle, " +
          "the collapsible CommandLine, ConnectOverlay, " +
          "the preserved `#elosern-action-live` live region and the " +
          "`#elosern-offline-overlay` hook.",
      },
    },
  },
};

export const CommandLineExpanded = {
  render: renderShell,
  args: {
    ...STATUS_SLICE_SAMPLE,
    connectionStatus: "ready",
    mode: "exploration",
    narrative: NARRATIVE_SAMPLE,
    prompt: PROMPT_SAMPLE,
    commandHistory: COMMAND_HISTORY_SAMPLE,
  },
  play: async ({ canvasElement }) => {
    const root = canvasElement?.querySelector('[data-testid="elosern-vue-root"]');
    await (root?.__elosernShell || mountedShell)?.focusCommandField();
  },
};

export const PreConnection = {
  render: renderShell,
  args: {
    connectionStatus: "connecting",
    connected: false,
    narrative: [],
    prompt: "",
    commandHistory: [],
  },
};

export const ReadyOfflinePreview = {
  render: renderShell,
  args: {
    ...STATUS_SLICE_SAMPLE,
    connectionStatus: "ready",
    mode: "exploration",
    narrative: NARRATIVE_SAMPLE,
    prompt: PROMPT_SAMPLE,
    commandHistory: COMMAND_HISTORY_SAMPLE,
  },
};

export const DisconnectedSession = {
  render: renderShell,
  args: {
    ...STATUS_SLICE_SAMPLE,
    connectionStatus: "offline",
    offline: true,
    narrative: NARRATIVE_SAMPLE,
    prompt: PROMPT_SAMPLE,
    commandHistory: COMMAND_HISTORY_SAMPLE,
  },
};

// Exercise the real composed shell: isolated component stories cannot expose
// overlap between the dock, the wrapped overview chips, the verb popover,
// the narrative and the command-line anchors.
// The stage-transition journey's panels for one stop
// (webclient-scene-transitions): the scene, the current map node, and the
// vitals, all full except the stop's hp, so the vitals island shows only on
// the stops that lower it.
function journeyPanels(stop) {
  const cell = stageJourneyLocalMap(stop.node).nodes.find((node) => node.current);
  return {
    art: { ...ART_PANEL_SAMPLE, scene: stageJourneyScene(stop) },
    local_map: stageJourneyLocalMap(stop.node),
    status: protocolFixtures.statusPanel({
      actor: { location: { label: cell.label, identity: cell.id } },
      resources: {
        hp: { current: stop.hp, maximum: 100 },
        mp: { current: 50, maximum: 50 },
        sp: { current: 40, maximum: 40 },
      },
    }),
  };
}

// The mode-transition journey's host (webclient-mode-transitions): the
// tavern keeper with a finished portrait, a greeting, and four picks.
// The catalog value is exactly `{artwork, context}`: the complete canonical
// descriptor (builtin-silhouette-stage-fallback rides as its own alpha
// terminal) plus its bounded display context.
const MODE_JOURNEY_CATALOG = {
  "7": {
    artwork: {
      subject_id: "npc_7",
      revision: "7".repeat(64),
      generation_subject: "npc_7",
      generation_state: "done",
      attempts: [
        {
          type: "image",
          source_id: "portrait.default:npc_7",
          rank: 30,
          resource: {
            resource_id: "defaults/elder.webp",
            version: "8".repeat(64),
            url: "/art/defaults/elder.webp",
            origin: "runtime",
            geometry: {
              image_size: null,
              face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
              stage: { scale: 1, x: 0, y: 0 },
              aspect_ratio: "3:4",
            },
          },
        },
      ],
      terminal: {
        kind: "alpha_mask",
        source_id: "portrait.alpha:elder",
        rank: 100,
        resource: {
          resource_id: "defaults/elder.webp",
          version: "9".repeat(64),
          url: "/art/defaults/elder.webp",
          origin: "silhouette",
          geometry: {
            image_size: null,
            face_rect: { x: 0.35, y: 0.03, w: 0.29, h: 0.16 },
            stage: null,
            aspect_ratio: "3:4",
          },
        },
      },
      retention_sources: [],
    },
    context: { name: "店長", role: "對話對象" },
  },
};
const MODE_JOURNEY_DIALOGUE = {
  schema_version: 2, available: true, kind: "dialogue",
  host: { identity: 7, display_name: "店長", portrait_ref: "7" },
  bond_stage: "熟識",
  line: "又見面了。今晚爐火正旺，要喝點什麼，還是想打聽些消息？",
  choices: [
    { keyword_id: "news", label: "最近有什麼消息？" },
    { keyword_id: "town", label: "關於這座城鎮" },
    { keyword_id: "guild", label: "冒險者公會在哪裡？" },
    { keyword_id: "rest", label: "我想稍作休息" },
  ],
};
const MODE_JOURNEY_DIALOGUE_CLOSED = {
  schema_version: 2, available: false, reason: { code: "dialogue_unavailable", message: "對話已結束" },
};

// The combat panel with `foes` active foes (webclient-combat-foes-on-stage):
// the player's side — the player and the first `companions` slots of the
// full party sample, so every drawn companion has its participant row and
// its plate its numbers (webclient-combat-formation) — then the foes in
// presenter order, each with a catalog portrait; `overrides` edits a foe by
// identity (a defeat, a missing ref).
// `downed`: the companion indexes that are knocked out (webclient-combat-
// defeated-foes: they kneel in their slots with a 倒地 plate).
const partyParticipants = (companions, downed = []) => [
  PARTY_PARTICIPANTS[0],
  ...PARTY_PANEL_FULL_SAMPLE.slots.slice(0, companions).map((slot, index) => ({
    identity: slot.identity,
    token: `a${index + 2}`,
    display_name: slot.display_name,
    team: "party",
    state: downed.includes(index) ? "knocked_out" : "active",
    hp_current: downed.includes(index) ? 0 : slot.hp_current,
    hp_maximum: slot.hp_maximum,
    portrait_ref: slot.portrait_ref,
    conditions: [],
  })),
];
// `conditions` spreads the plate conditions and low hit points over the
// roster (webclient-combat-figure-plates).
const combatPanelWith = (foes, overrides = {}, companions = 2, conditions = false, downed = []) => {
  const roster = [...partyParticipants(companions, downed), ...foeParticipants(foes, overrides)];
  return protocolFixtures.combatActions({ ...combatRoster(conditions ? withPlateConditions(roster) : roster) });
};
const combatRoster = (participants) => ({ participants, skills: combatSkills(participants) });
const combatArt = (art) => ({
  ...art,
  portrait_catalog: { ...(art.portrait_catalog || {}), ...COMPANION_PORTRAIT_CATALOG, ...FOE_PORTRAIT_CATALOG },
});

const renderPlayer = (args) => ({
  setup() {
    const host = ref(null);
    const pinia = createPinia();
    const store = useElosernStore(pinia);
    let app;
    let bridge;
    let journeyTimer = null;
    let savedStorage = null;
    onMounted(async () => {
      app = createApp(AppClient);
      app.use(pinia);
      bridge = createWindowBridge(store);
      app.mount(host.value);
      store.beginTransport(1);
      store.setConnected(true);
      store.setLoggedIn(true);
      // A story's motion level must not outlive it: the store persists the
      // choice, so the page's storage is restored on unmount.
      if (args.motionLevel) {
        savedStorage = Object.keys(window.localStorage).map((key) => [key, window.localStorage.getItem(key)]);
        store.setMotionLevel(args.motionLevel);
      }
      const snapshot = protocolFixtures.snapshot({
        mode: args.dialogue ? "dialogue" : args.combat ? "combat" : "exploration",
        panels: {
          status: protocolFixtures.statusPanel(args.populated || args.combat ? {
            conditions: [
              { code: "poisoned", label: "中毒", provenance: { kind: "non_equipment", equipment_sources: [] }, severity: "harmful", remaining_seconds: 40 },
              { code: "blessed", label: "祝福", provenance: { kind: "non_equipment", equipment_sources: [] }, severity: "beneficial" },
            ],
          } : undefined),
          // The populated island stacks (webclient-avg-stage-hud-anchors):
          // standing companions and three tracked objectives,
          // so the `map` anchor shows the objective line with `+2`.
          ...(args.populated || args.combat ? {
            party: {
              ...PARTY_PANEL_FULL_SAMPLE,
              slots: PARTY_PANEL_FULL_SAMPLE.slots.slice(0, args.companions ?? 2).map((s) => ({ ...s, portrait_ref: args.placeholders ? null : String(s.identity) })),
            },
            objectives: OBJECTIVES_PANEL_SAMPLE,
            art: args.combat ? combatArt(ART_PANEL_SAMPLE) : {
              ...ART_PANEL_SAMPLE, portrait_catalog: { ...ART_PANEL_SAMPLE.portrait_catalog, ...COMPANION_PORTRAIT_CATALOG },
            },
          } : {}),
          exploration: protocolFixtures.explorationPanel({
            // Exits labelled by direction, as the server labels them: the
            // choice list's `↦ 移動…` rows then show each direction's glyph
            // and the destination's name.
            ...(args.dialogue ? { move: [
              { exit_ref: "east", label: "東", destination: "room:43", enabled: true, disabled_reason: null },
              { exit_ref: "north", label: "北", destination: "room:44", enabled: false, disabled_reason: { code: "blocked", message: "門被鎖住了" } },
            ] } : {}),
            interact: [
              // The tavern keeper's finished portrait IS catalogued by the
              // variants whose art panel carries the `"7"` entry (the
              // dialogue and mode-journey panels), so the schema-4 descriptor
              // carries that reference; where the committed panel has no such
              // entry the medallion falls back to the initial, truthfully.
              // The guard carries none and never shows a face.
              { identity: 7, display_name: "店長", portrait_ref: "7", affordances: [
                { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
              ] },
              { identity: 8, display_name: "守衛", portrait_ref: null, affordances: [
                { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
              ] },
              // The exploration companion-focus variants (reuse-lineup-person-
              // focus 3.1): a member of the SAME committed party panel is
              // present as an interact target, so its medallion opens the verb
              // card for an identity the actor-left lineup already draws.
              ...(args.explorationFocus ? [{
                identity: args.explorationFocus,
                display_name: PARTY_PANEL_FULL_SAMPLE.slots.find(
                  (slot) => slot.identity === args.explorationFocus,
                )?.display_name ?? "同行",
                portrait_ref: null,
                affordances: [
                  { kind: "action", action_id: "explore.talk_open", label: "交談", enabled: true, disabled_reason: null },
                ],
              }] : []),
            ],
          }),
          context_actions: args.combat ? combatPanelWith(args.combat === true ? 3 : args.combat, args.foeOverrides || {}, args.companions ?? 2, !!args.conditions, args.downedCompanions || []) : protocolFixtures.explorationActions({
            suggestions: { status: "ready", cards: [
              { kind: "known_action", action_code: "explore.look", label: "查看房間", params: { room: true } },
              { kind: "known_action", action_code: "explore.wait", label: "等到黃昏", params: { daypart: "dusk" } },
              { kind: "known_action", action_code: "explore.look", label: "查看木箱", params: { target_id: 3 } },
            ] },
          }),
          local_map: protocolFixtures.localMapPanel(),
          ...(args.journey ? journeyPanels(STAGE_JOURNEY_STOPS[0]) : {}),
          services: SERVICES_PANEL_SAMPLE,
          character: CHARACTER_PANEL_SAMPLE,
          roster: {
            schema_version: 3,
            available: true,
            characters: [
              {
                identity: 1,
                name: "艾莉亞",
                current: true,
                pending: false,
                portrait: args.grounding ? {
                  subject_id: "portrait:character:1",
                  revision: "1".repeat(64),
                  generation_subject: "portrait:character:1",
                  generation_state: "missing",
                  attempts: [],
                  terminal: null,
                  retention_sources: [],
                } : {
                  subject_id: "portrait:character:1",
                  revision: "2".repeat(64),
                  generation_subject: "portrait:character:1",
                  generation_state: "done",
                  attempts: [
                    {
                      type: "image",
                      source_id: "portrait.default:portrait:character:1",
                      rank: 30,
                      resource: {
                        resource_id: "defaults/man.webp",
                        version: "3".repeat(64),
                        url: "/art/defaults/man.webp",
                        origin: "runtime",
                        geometry: {
                          image_size: null,
                          face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
                          stage: { scale: 1, x: 0, y: 0 },
                          aspect_ratio: "3:4",
                        },
                      },
                    },
                  ],
                  terminal: null,
                  retention_sources: [],
                },
              },
            ],
            max_characters: 5,
            can_create: true,
            switch_locked: false,
            lock_reason: null,
          },
          // The dialogue host's catalog entry (webclient-dialogue-stage-
          // actors): an image, a pending placeholder card, or no entry at all
          // (`portrait_ref` null → the name's initial and the name).
          ...(args.dialogue && args.dialogue !== "missing" ? { art: {
            ...ART_PANEL_PENDING_SAMPLE,
            // A local scene image for layout review (optional arg).
            ...(args.sceneUrl ? { scene: sceneBlock({}, sceneDescriptor({
              attempts: [{
                type: "image",
                source_id: `scene.generated:${SCENE_SUBJECT}`,
                rank: 20,
                resource: sceneResource({
                  resource_id: args.sceneUrl,
                  version: fixtureDigest(args.sceneUrl),
                  url: args.sceneUrl,
                }),
              }],
            })) } : {}),
            portrait_catalog: {
              ...(args.populated ? COMPANION_PORTRAIT_CATALOG : {}),
              "7": args.dialogue === "pending" ? {
                artwork: {
                  ...MODE_JOURNEY_CATALOG["7"].artwork,
                  generation_state: "pending",
                  attempts: [],
                },
                context: { name: "店長", role: "對話對象" },
              } : MODE_JOURNEY_CATALOG["7"],
            },
          } } : {}),
          ...(args.dialogue ? { dialogue: {
            schema_version: 2, available: true, kind: "dialogue",
            host: { identity: 7, display_name: args.dialogue === "missing" ? "合成‧旅人" : "店長", portrait_ref: args.dialogue === "missing" ? null : "7" },
            bond_stage: "熟識",
            line: "歡迎來到西風酒館。你可以在這裡打聽消息，也可以稍作休息再出發。",
            choices: [
              { keyword_id: "news", label: "最近有什麼消息？" },
              { keyword_id: "town", label: "關於這座城鎮" },
              { keyword_id: "guild", label: "冒險者公會在哪裡？" },
              { keyword_id: "rest", label: "我想稍作休息" },
            ],
          } } : {}),
        },
      });
      if (args.companionSpeaks) {
        snapshot.panels.dialogue.host = { identity: 102, display_name: PARTY_PANEL_FULL_SAMPLE.slots[1].display_name, portrait_ref: "102" };
      }
      if (args.possession) {
        snapshot.panels.status.actor.identity = "102";
        snapshot.panels.possession_banner = { schema_version: 1, available: true, host_name: PARTY_PANEL_FULL_SAMPLE.slots[1].display_name, since_tick: 0 };
      }
      if (args.participantPolish) {
        const participants = [...PARTY_PARTICIPANTS, ...foeParticipants(4, {
          31: { display_name: "灰袍盜賊與北境巡防隊長的漫長稱號" },
          34: { state: "defeated", hp_current: 0 },
        })];
        snapshot.panels.context_actions = protocolFixtures.combatActions({
          participants, session: { round: 0 },
          skills: [{ category: "martial_arts", label: "武技", groups: [{ group: "basic", label: "基本", skills: [{
            key: CombatMenu.BASIC_ATTACK_KEY, label: "基本攻擊", description: "選擇一名敵人。",
            cost: {}, target_spec: "single", element: null, enabled: true, disabled_reason: null,
            targets: [31, 32, 33], shorthands: [], hostile: true, beneficial: false,
          }] }] }],
        });
        snapshot.panels.status = protocolFixtures.statusPanel({ combat: { mode: "hostile", round: 0 } });
        snapshot.panels.art.portrait_catalog["32"] = {
          artwork: {
            ...FOE_PORTRAIT_CATALOG["32"].artwork,
            generation_state: "pending",
            attempts: [],
            terminal: null,
          },
          context: { name: "盜賊頭目", role: "敵方" },
        };
      }
      const result = store.receive(1, "ui_snapshot", [snapshot], {});
      if (!result.accepted || store.lastPanelRejection) throw new Error(`Player layout fixture was rejected: ${JSON.stringify(store.lastPanelRejection || result)}`);
      if (args.pane) store.tabToRootAndConfirm(args.pane, "pointer");
      // A combat line in the message window, so the band shows the message
      // region spanning it while the command card stands at the stage centre
      // (webclient-combat-command-card-centred).
      if (args.combat && !args.participantPolish) {
        store.appendText("out", "灰袍盜賊掀翻木桌，與同夥拔出短刀，一步步逼近。");
      }
      // `combatKeys` (webclient-combat-command-card-centred): router keys
      // replayed through the store's keyboard entry once the snapshot has
      // committed, so a story opens a deeper frame of the command card.
      for (const key of args.combatKeys || []) {
        await nextTick();
        store.focusPress(key, false);
      }
      // `combatFocus`: then focus one row of that frame by its key.
      if (args.combatFocus) {
        await nextTick();
        store.focusItemByKey(args.combatFocus);
      }
      // The exploration companion-focus variants (reuse-lineup-person-focus
      // 3.1): the client-local verb card of a RENDERED companion. Opening it
      // lights that existing actor-left figure and lifts it above every
      // baseline with no actor-right copy; `explorationFocusClosed` closes it
      // again in the same run, so the restored baseline is on screen too. The
      // host exposes `__companionFocus.open()`/`.close()` for a reviewer.
      // Fixture rendering only: the wire acceptance of this join is the managed
      // browser journey and the store-driven Vitest regressions.
      if (args.explorationFocus) {
        const focusKey = `target-${args.explorationFocus}`;
        const focus = {
          store,
          open: () => store.activatePresence(focusKey),
          close: () => store.closePresenceCard(),
        };
        host.value.__companionFocus = focus;
        window.__companionFocus = focus;
        store.activatePresence(focusKey);
        if (args.explorationFocusClosed) store.closePresenceCard();
      }
      if (args.participantPolish) {
        let revision = 1;
        const sender = protocolFixtures.createFakeSender();
        store.setSender(sender);
        const round = (terminal = false) => {
          const request = store.dispatchAction("combat.cast", { skill_key: CombatMenu.BASIC_ATTACK_KEY, target_ids: [31] });
          const beats = [
            { seq: 0, action: 0, kind: "roll", actor: "32", target: "31", amount: null, hp_after: null, text: "敵人舉起武器。" },
            { seq: 1, action: 1, kind: "damage", actor: "32", target: "31", amount: 20, hp_after: 10, text: "武器命中，生命值下降。" },
          ];
          beats.forEach((beat) => store.appendText("out", beat.text));
          const panels = {
            context_actions: terminal ? protocolFixtures.explorationActions() : protocolFixtures.combatActions({
              skills: snapshot.panels.context_actions.skills,
              session: { round: revision },
              participants: snapshot.panels.context_actions.participants.map((p) => p.identity === 31 ? { ...p, hp_current: 10 } : p),
            }),
            status: protocolFixtures.statusPanel({ combat: terminal ? null : { mode: "hostile", round: revision } }),
            combat_beats: { schema_version: 1, available: true, round: `polish/${revision}`, beats },
          };
          const received = store.receive(1, "ui_update", [protocolFixtures.update({
            revision: ++revision, mode: terminal ? "exploration" : "combat", panels,
          })], {});
          if (!received.accepted || store.lastPanelRejection) throw new Error(JSON.stringify(store.lastPanelRejection || received));
          store.receive(1, "ui_action_result", [protocolFixtures.actionResult({ request_id: request, presentation_revision: revision })], {});
        };
        window.__participantPolish = { store, sent: sender.sent, round };
        host.value.__participantPolish = window.__participantPolish;
      }
      // The session line as the narrative delivers it (webclient-dialogue-
      // choices-overlay D2): paged verbatim under the name plate. On mount
      // the window shows the last page complete, so the choice list shows at
      // once; `lateGreeting` delivers it after mount, so it types first.
      if (args.dialogue) {
        const hostName = args.dialogue === "missing" ? "合成‧旅人" : "店長";
        const deliver = () =>
          store.appendText("out", `${hostName}說：「${args.greeting || "歡迎來到西風酒館。你可以在這裡打聽消息，也可以稍作休息再出發。"}」`);
        if (args.lateGreeting) setTimeout(deliver, 400);
        else deliver();
      }
      // The player speaking: a pick in flight (no transport is attached, so
      // the request stays open and the player stays lit).
      if (args.playerSpeaking) store.dispatchAction("explore.talk_scripted", { npc_id: 7, keyword_id: "news" }, null);
      // The `↦ 移動…` swap: the list shows the committed overview's exits.
      if (args.moveExits) {
        // The list renders once the fonts are ready and the line is read.
        for (let tries = 0; tries < 60; tries += 1) {
          const row = host.value?.querySelector('[data-testid="dialogue-move"]');
          if (row) {
            row.click();
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 50));
        }
      }
      // The stage-transition journey (webclient-scene-transitions): each
      // step acts, commits the next stop's scene, location, map node, and
      // vitals, then delivers its line, exactly as a move does live. The
      // host exposes `step()` so a reviewer (or a browser driving the story)
      // can take one step at a time; `autoplay` walks on its own.
      if (args.journey) {
        store.appendText("out", STAGE_JOURNEY_STOPS[0].line);
        let index = 0;
        let revision = 1;
        const step = () => {
          index = (index + 1) % STAGE_JOURNEY_STOPS.length;
          const stop = STAGE_JOURNEY_STOPS[index];
          revision += 1;
          store.appendText("in", stop.command);
          store.receive(1, "ui_update", [protocolFixtures.update({ revision, panels: journeyPanels(stop) })], {});
          store.appendText("out", stop.line);
          return index;
        };
        const journey = { step, store };
        host.value.__stageJourney = journey;
        window.__stageJourney = journey;
        if (args.autoplay) {
          journeyTimer = setInterval(step, 3600);
        }
      }
      // The mode-transition journey (webclient-mode-transitions): the real
      // client walks exploration -> dialogue -> exploration -> combat ->
      // exploration, one committed revision per step, exactly as the server
      // commits them. The host exposes `__modeJourney.go(step)` so a
      // reviewer (or a browser driving the story) takes one step at a time;
      // `autoplay` walks on its own.
      if (args.modeJourney) {
        let revision = 1;
        const art = {
          ...ART_PANEL_SAMPLE,
          scene: stageJourneyScene(STAGE_JOURNEY_STOPS[2]),
          portrait_catalog: { ...MODE_JOURNEY_CATALOG, ...COMPANION_PORTRAIT_CATALOG, ...FOE_PORTRAIT_CATALOG },
        };
        const foes = args.modeJourneyFoes || 3;
        const companions = args.populated ? args.companions ?? 2 : 0;
        const commit = (mode, panels, line) => {
          revision += 1;
          store.receive(1, "ui_update", [protocolFixtures.update({ revision, mode, panels })], {});
          if (line) store.appendText("out", line);
        };
        const steps = {
          talk: () => {
            store.appendText("in", "與店長交談");
            commit("dialogue", { art, dialogue: MODE_JOURNEY_DIALOGUE }, `店長說：「${MODE_JOURNEY_DIALOGUE.line}」`);
          },
          leave: () => {
            store.appendText("in", "結束對話");
            commit("exploration", { dialogue: MODE_JOURNEY_DIALOGUE_CLOSED }, "你向店長點頭致意，轉身離開吧檯。爐火在身後劈啪作響。");
          },
          fight: () => {
            store.appendText("in", "攻擊灰袍盜賊");
            commit("combat", { context_actions: combatPanelWith(foes, {}, companions) }, "灰袍盜賊猛然掀翻木桌，短刀在火光中一閃！");
          },
          // Inside combat (webclient-combat-foes-on-stage): the front foe is
          // defeated, fades where it stands, and the others step forward.
          defeat: () => {
            store.appendText("in", "攻擊灰袍盜賊");
            commit("combat", { context_actions: combatPanelWith(foes, { 31: { state: "defeated", hp_current: 0 } }, companions) }, "灰袍盜賊踉蹌倒地，再也沒有起來。");
          },
          flee: () => {
            store.appendText("in", "逃跑");
            commit("exploration", { context_actions: protocolFixtures.explorationActions() }, "你撞開後門衝進夜色，身後的叫罵聲漸漸遠去。");
          },
        };
        const order = args.modeJourneyOrder || ["talk", "leave", "fight", "defeat", "flee"];
        let next = 0;
        const go = (name) => {
          const key = name || order[next];
          next = (order.indexOf(key) + 1) % order.length;
          steps[key]();
          return key;
        };
        store.receive(1, "ui_update", [protocolFixtures.update({ revision: (revision += 1), mode: "exploration", panels: { art } })], {});
        store.appendText("out", STAGE_JOURNEY_STOPS[2].line);
        const journey = { go, store };
        host.value.__modeJourney = journey;
        window.__modeJourney = journey;
        if (args.autoplay) {
          journeyTimer = setInterval(() => go(), 3200);
        }
      }
      if (args.practice) {
        store.openHudDrawer("skill");
        await nextTick();
        host.value?.querySelector('button[aria-label^="修煉"]')?.click();
      }
    });
    onBeforeUnmount(() => {
      if (journeyTimer !== null) clearInterval(journeyTimer);
      if (savedStorage) {
        window.localStorage.clear();
        savedStorage.forEach(([key, value]) => window.localStorage.setItem(key, value));
      }
      if (window.__stageJourney && host.value?.__stageJourney === window.__stageJourney) delete window.__stageJourney;
      if (window.__modeJourney && host.value?.__modeJourney === window.__modeJourney) delete window.__modeJourney;
      if (window.__participantPolish && host.value?.__participantPolish === window.__participantPolish) delete window.__participantPolish;
      if (window.__companionFocus && host.value?.__companionFocus === window.__companionFocus) delete window.__companionFocus;
      bridge?.uninstall();
      app?.unmount();
      disposePinia(pinia);
    });
    return () => h("div", { ref: host, style: "height:100vh;min-height:0" });
  },
});

export const ActionNavigation = { render: renderPlayer, args: {} };
// A person chip's verb popover (webclient-scene-overview-swap): the overview
// stays rendered beneath it while the popover's card covers the pane.
export const VerbPopoverSelector = { render: renderPlayer, args: { pane: "target-7" } };
// Dialogue (webclient-dialogue-stage-actors; webclient-dialogue-choices-
// overlay): the command region collapses, the message window pages the
// session line under the host's name plate, the host stands opposite the
// player — lit while speaking, the player dimmed — and the choice list sits
// centred over the stage once the line is read.
export const DialogueSelector = { render: renderPlayer, args: { dialogue: true } };
// The choice list's `↦ 移動…` swap (webclient-dialogue-choices-overlay):
// the committed overview's exits with their glyphs, a locked exit with its
// reason, and the back row.
export const DialogueMoveExits = { render: renderPlayer, args: { dialogue: true, moveExits: true } };
// The greeting arrives after mount, so it types under the name plate with no
// choice list; the list appears centred over the stage and takes focus once
// the last page is fully shown.
export const DialogueGreetingTypes = { render: renderPlayer, args: { dialogue: true, lateGreeting: true } };
// The player's pick is in flight: the player is lit and the host dimmed.
export const DialoguePlayerSpeaking = { render: renderPlayer, args: { dialogue: true, playerSpeaking: true } };
// The host's catalog entry is still generating: its own placeholder card.
export const DialogueHostPending = { render: renderPlayer, args: { dialogue: "pending" } };
// The host is not in the catalog: the name's initial and the name.
export const DialogueHostMissing = { render: renderPlayer, args: { dialogue: "missing" } };
export const WaitingSelector = { render: renderPlayer, args: { pane: "wait" } };
export const PracticeScreen = { render: renderPlayer, args: { practice: true } };
// The island anchors populated (webclient-avg-stage-hud-anchors): vitals,
// a harmful condition, and the standing party at the left; the place
// card, the minimap, and the one-line objective at the top-right.
export const PopulatedHud = { render: renderPlayer, args: { populated: true } };
export const PopulatedFullParty = { render: renderPlayer, args: { populated: true, companions: 4 } };
export const PopulatedSolo = { render: renderPlayer, args: { populated: true, companions: 0 } };
export const PopulatedPossession = { render: renderPlayer, args: { populated: true, companions: 4, possession: true } };
export const PopulatedPlaceholders = { render: renderPlayer, args: { populated: true, companions: 4, placeholders: true } };
// The exploration companion focus (reuse-lineup-person-focus 3.1): the
// committed party's own companion is the interact target, so its medallion
// opens the client-local verb card ON the existing actor-left figure — lit with
// the highest z — while the other companions keep the listener dim and the
// controlled figure keeps its own props. Fixture rendering; the real join
// acceptance is the managed browser journey.
export const ExplorationCompanionFocus = {
  render: renderPlayer,
  args: { populated: true, companions: 2, explorationFocus: 101 },
};
// The same committed lineup after that card closes: every figure is back on the
// current baseline, with no remembered focus z and no right-side standee.
export const ExplorationCompanionFocusRestored = {
  render: renderPlayer,
  args: { populated: true, companions: 2, explorationFocus: 101, explorationFocusClosed: true },
};
export const DialogueFullParty = { render: renderPlayer, args: { populated: true, companions: 4, dialogue: true } };
export const DialogueCompanionSpeaks = { render: renderPlayer, args: { populated: true, companions: 4, dialogue: true, companionSpeaks: true } };
// Combat: the `map` anchor (place card, minimap, objective line) is hidden,
// both sides stand in one shared-scale formation with glance plates, and the
// command menu is the narrow card at the stage's dead centre, in the gap the
// formation keeps clear, while the message window spans the band
// (webclient-combat-command-card-centred).
export const CombatHud = { render: renderPlayer, args: { combat: true } };
// The combat command card's deeper frames (webclient-combat-command-card-
// centred), reached through the router's own keys: the AREA target step
// (技能 → 元素魔法 → 火 → 火風暴), a skill detail, a disabled command's
// reason, and a master's 威力 step (火球).
export const CombatTargetStep = {
  render: renderPlayer,
  args: { combat: true, combatKeys: ["ArrowDown", "Enter", "ArrowDown", "Enter", "Enter", "ArrowDown", "ArrowDown", "Enter"], combatFocus: "area-32" },
};
export const CombatSkillDetail = {
  render: renderPlayer,
  args: { combat: true, combatKeys: ["ArrowDown", "Enter", "ArrowDown", "Enter", "Enter", "ArrowDown"] },
};
export const CombatDisabledCommand = { render: renderPlayer, args: { combat: true, combatKeys: ["ArrowDown", "ArrowDown"] } };
export const CombatMasterScale = {
  render: renderPlayer,
  args: { combat: true, combatKeys: ["ArrowDown", "Enter", "ArrowDown", "Enter", "Enter", "ArrowDown", "Enter"], combatFocus: "scale-2" },
};
// Four foes (one defeated), a long foe name ellipsized on its plate. The
// offline journey exposes round()/round(true) for normal/terminal playback.
export const CombatParticipantPolish = { render: renderPlayer, args: { combat: 4, participantPolish: true } };
// The foe line-up (webclient-combat-foes-on-stage) with one foe, and with
// five, every one of whom stands in the formation.
export const CombatOneFoe = { render: renderPlayer, args: { combat: 1 } };
export const GroundedOneFoe = { render: renderPlayer, args: { combat: 1, grounding: "missing" } };
export const GroundedTwoFoes = { render: renderPlayer, args: { combat: 2, grounding: "pending" } };
export const GroundedThreeFoes = { render: renderPlayer, args: { combat: 3, grounding: "failed" } };
export const CombatFiveFoes = { render: renderPlayer, args: { combat: 5 } };
// The combat formation (webclient-combat-formation design D6): the corners
// of the party × foe matrix, each at the shared scale the engine picks for
// the viewport — review them at 1451x790 and at 1600x900, with the command
// card standing in the formation's dead-centre gap. The party is the
// player plus `companions`; foes run up to the participant cap (16).
export const CombatSoloOneFoe = { render: renderPlayer, args: { combat: 1, companions: 0 } };
export const CombatSoloFifteenFoes = { render: renderPlayer, args: { combat: 15, companions: 0 } };
export const CombatThreeFiguresFiveFoes = { render: renderPlayer, args: { combat: 5, companions: 2 } };
export const CombatFullPartyOneFoe = { render: renderPlayer, args: { combat: 1, companions: 4 } };
export const CombatFullPartyEightFoes = { render: renderPlayer, args: { combat: 8, companions: 4 } };
export const CombatFullPartyElevenFoes = { render: renderPlayer, args: { combat: 11, companions: 4 } };
// The plates' conditions and low-HP alarm (webclient-combat-figure-plates)
// at the matrix corners: compact plates (solo against fifteen) and a full
// party against eight. Hover a glyph, or Tab past the dock into the plates
// group (戰場) and walk it with the arrow keys.
export const CombatConditionsSoloFifteenFoes = { render: renderPlayer, args: { combat: 15, companions: 0, conditions: true } };
export const CombatConditionsFullParty = { render: renderPlayer, args: { combat: 8, companions: 4, conditions: true } };
// Fallen figures (webclient-combat-defeated-foes): six foes, two of them
// defeated (one knocked out, one defeated), keep their slots collapsed under
// a broken seal with ✕ 已擊破 plates, and a knocked-out companion kneels
// with a ▼ 倒地 plate; the formation keeps every slot, so nothing re-forms.
export const CombatSomeFoesDefeated = {
  render: renderPlayer,
  args: {
    combat: 6,
    companions: 2,
    foeOverrides: {
      32: { state: "knocked_out", hp_current: 0 },
      34: { state: "defeated", hp_current: 0 },
    },
    downedCompanions: [1],
  },
};
// Exploration → combat → exploration at `full`: the party glides and scales
// from its exploration row into the formation while the foes enter at the
// same height as the flash releases, then the plates rise; leaving combat
// glides the party back. `__modeJourney.go('fight' | 'defeat' | 'flee')`.
export const CombatEnterJourney = {
  render: renderPlayer,
  args: { modeJourney: true, autoplay: true, populated: true, companions: 2, modeJourneyFoes: 5, modeJourneyOrder: ["fight", "defeat", "flee"] },
};
// The same journey at `reduced`: every figure takes its final box in the
// commit's frame; only entering and leaving figures and plates fade.
export const CombatReducedMotion = {
  render: renderPlayer,
  args: { modeJourney: true, autoplay: true, populated: true, companions: 2, modeJourneyFoes: 5, modeJourneyOrder: ["fight", "defeat", "flee"], motionLevel: "reduced" },
};
// The stage transitions (webclient-scene-transitions): a walk down a short
// street. Each step crossfades the scene once the next painting is decoded,
// slides the place card's new heading in, pans the minimap from the node the
// player left, clears the message window for the new line, and reveals or
// hides the vitals island as hp drops and recovers. It walks on its own
// every few seconds; the host element's `__stageJourney.step()` takes one
// step on demand.
export const StageJourney = { render: renderPlayer, args: { journey: true, autoplay: true } };
// The mode transitions (webclient-mode-transitions): the real client opens a
// conversation (the command panel slides out over the widened message
// window, the host walks on from the right, the name plate fades in, and
// the choices stagger in once the greeting is read), ends it (the reverse),
// then enters combat (the flash, the veil, the command card fading in at the
// stage centre, and the foes stepping in as the flash releases), defeats the front foe (it fades and
// the others step forward), and leaves combat (the foes fade out and the
// band's command panel flips back).
// It walks on its own every few seconds; the host element's
// `__modeJourney.go(step)` takes one step on demand
// (`talk`, `leave`, `fight`, `defeat`, `flee`).
export const ModeJourney = { render: renderPlayer, args: { modeJourney: true, autoplay: true } };
