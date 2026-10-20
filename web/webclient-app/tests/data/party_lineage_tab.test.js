// webclient-party-lineage-tab: the party window's 系譜 tab (design §6.5).
// The list groups the viewed member's committed `lineage` v2 graphs by their
// element/style label, names each row by its supplied roots joined with ‧,
// draws one diamond per node (filled capped, half owned, dashed locked) with
// the committed owned/total, 可解鎖 and 已全數見頂; the detail draws the
// selected graph by `depth` with each merge node once, every edge labelled
// with its minimum level, and the node states told apart by border and text;
// an owned node opens its skill on 技能 (the tab's own selection dispatch
// tells the server), and the 技能 tab's link opens the skill's graph. Every
// value is the payload's; nothing is invented for an unavailable panel.
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PartyLineageTab from "../../components/PartyLineageTab.vue";
import PartySkillTab from "../../components/PartySkillTab.vue";
import PartyWindow from "../../components/PartyWindow.vue";
import { rememberPartyWindowTab, resetPartyWindowMemory } from "../../components/party-window-memory.js";
import { graphLayout, groupGraphs, nodeGrowth, nodeState, prereqParts, rootName } from "../../components/party-lineage-model.js";
import { PARTY_WINDOW_PANEL_SAMPLE } from "../../stories/fixtures/party_panels.js";
import { CHARACTER_SKILL_COMPANION_SAMPLE } from "../../stories/fixtures/skill_tab_panels.js";
import {
  LINEAGE_COMPANION_SAMPLE,
  LINEAGE_EMPTY_SAMPLE,
  LINEAGE_HOLY_WATER_GRAPH,
  LINEAGE_ICE_GRAPH,
  LINEAGE_PRAYER_GRAPH,
  LINEAGE_STAFF_GRAPH,
  LINEAGE_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures/lineage_tab_panels.js";

// Payload values are read from the fixtures, never restated here.
const PANEL = LINEAGE_COMPANION_SAMPLE;
const CHARACTER = CHARACTER_SKILL_COMPANION_SAMPLE;
const MEMBER = PARTY_WINDOW_PANEL_SAMPLE.slots.find((row) => row.identity === CHARACTER.member_id);
const ICE = LINEAGE_ICE_GRAPH;
const nodeOf = (graph, predicate) => graph.nodes.find(predicate);
const CAPPED_ROOT = nodeOf(ICE, (n) => n.capped);
const OWNED_ROOT = nodeOf(ICE, (n) => n.owned && !n.capped);
const READY = nodeOf(ICE, (n) => n.ready);
// The merge node: the one with two incoming edges.
const MERGE_KEY = ICE.edges.map((e) => e.to_key).find((key, i, all) => all.indexOf(key) !== i);
const MERGE = nodeOf(ICE, (n) => n.skill_key === MERGE_KEY);
const LOCKED = nodeOf(ICE, (n) => !n.owned && !n.ready && n.prereq_text_zh && n.skill_key !== MERGE_KEY);
const nameOf = (graph, key) => nodeOf(graph, (n) => n.skill_key === key).display_name_zh;
const rootsJoined = (graph) => graph.root_keys.map((key) => nameOf(graph, key)).join(" ‧ ");

describe("party-lineage-model", () => {
  it("groups graphs by label in first-appearance order and names them by their roots", () => {
    const groups = groupGraphs(PANEL);
    expect(groups.map((g) => g.label)).toEqual([...new Set(PANEL.graphs.map((g) => g.group_label_zh))]);
    const shared = groups.find((g) => g.graphs.length > 1);
    expect(shared.graphs.map((g) => g.graph_id)).toEqual([LINEAGE_PRAYER_GRAPH.graph_id, LINEAGE_HOLY_WATER_GRAPH.graph_id]);
    expect(rootName(ICE)).toBe(rootsJoined(ICE));
    expect(rootName({ ...ICE, root_keys: [...ICE.root_keys, "absent_root"] })).toBe(rootsJoined(ICE));
    expect(groupGraphs(LINEAGE_UNAVAILABLE_SAMPLE)).toEqual([]);
    expect(groupGraphs(null)).toEqual([]);
  });

  it("derives the node state from ownership alone", () => {
    expect(nodeState(CAPPED_ROOT)).toBe("capped");
    expect(nodeState(OWNED_ROOT)).toBe("owned");
    expect(nodeState(READY)).toBe("locked");
    // An owned node whose prerequisite is unmet keeps its owned state.
    expect(nodeState({ ...OWNED_ROOT, usable: false, prereq_text_zh: LOCKED.prereq_text_zh })).toBe("owned");
  });

  it("formats the committed growth band without a growth rule", () => {
    const band = OWNED_ROOT.xp_into_level + OWNED_ROOT.xp_to_next_level;
    expect(nodeGrowth(OWNED_ROOT)).toEqual({
      capped: false,
      levelText: `Lv ${OWNED_ROOT.level}`,
      percent: Math.round((OWNED_ROOT.xp_into_level / band) * 100),
      xpText: `${OWNED_ROOT.xp_into_level}/${band} → 下一階`,
    });
    expect(nodeGrowth({ ...OWNED_ROOT, xp_into_level: 23, xp_to_next_level: 27 }).xpText).toBe("23/50 → 下一階");
    expect(nodeGrowth(CAPPED_ROOT)).toMatchObject({ capped: true, percent: 100, xpText: "見頂" });
    expect(nodeGrowth({ ...OWNED_ROOT, xp_into_level: 0, xp_to_next_level: 0 }).percent).toBe(0);
    expect(nodeGrowth(READY)).toBeNull();
  });

  it("splits a prerequisite line only between its clauses, losing nothing", () => {
    const parts = prereqParts(MERGE.prereq_text_zh);
    expect(parts.join("")).toBe(MERGE.prereq_text_zh);
    expect(parts.length).toBe((MERGE.prereq_text_zh.match(/「/g) || []).length);
    expect(prereqParts(LOCKED.prereq_text_zh)).toEqual([LOCKED.prereq_text_zh]);
    expect(prereqParts("")).toEqual([]);
  });

  it("lays nodes out by depth in payload order and skips an edge to an absent node", () => {
    const layout = graphLayout(ICE);
    expect(layout.rows).toBe(Math.max(...ICE.nodes.map((n) => n.depth)) + 1);
    for (const n of ICE.nodes) {
      const row = ICE.nodes.filter((m) => m.depth === n.depth);
      expect(layout.positions[n.skill_key].x).toBeCloseTo(((row.indexOf(n) + 0.5) / row.length) * 100);
      expect(layout.positions[n.skill_key].y).toBeCloseTo(((n.depth + 0.5) / layout.rows) * 100);
    }
    // A lone node in its row (the merge) centres itself.
    expect(layout.positions[MERGE_KEY].x).toBe(50);
    expect(layout.edges).toHaveLength(ICE.edges.length);
    const dangling = graphLayout({ ...ICE, edges: [...ICE.edges, { from_key: MERGE_KEY, to_key: "absent", min_level: 1 }] });
    expect(dangling.edges).toHaveLength(ICE.edges.length);
    // Unsorted nodes land on the same rows.
    const shuffled = graphLayout({ ...ICE, nodes: [...ICE.nodes].reverse() });
    expect(shuffled.rows).toBe(layout.rows);
    expect(shuffled.positions[MERGE_KEY]).toEqual(layout.positions[MERGE_KEY]);
    expect(graphLayout({ ...ICE, nodes: [] })).toBeNull();
  });
});

describe("PartyLineageTab", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountTab(props = {}) {
    wrapper = mount(PartyLineageTab, { attachTo: document.body, props: { member: MEMBER, lineage: PANEL, ...props } });
    return wrapper;
  }

  const row = (w, id) => w.get(`[data-testid="party-lineage-tab__row"][data-graph="${id}"]`);
  const node = (w, key) => w.get(`[data-testid="party-lineage-tab__node"][data-key="${key}"]`);

  it("lists the graphs under their group headings with the completion summary", () => {
    const w = mountTab();
    expect(w.get('[data-testid="party-lineage-tab__summary"]').text()).toBe(`已完成 ${PANEL.completed_count} / ${PANEL.total_count} 樹`);
    expect(w.findAll('[data-testid="party-lineage-tab__group-label"]').map((el) => el.text())).toEqual(groupGraphs(PANEL).map((g) => g.label));
    expect(w.findAll('[data-testid="party-lineage-tab__row"]').map((el) => el.attributes("data-graph"))).toEqual(PANEL.graphs.map((g) => g.graph_id));
    for (const graph of PANEL.graphs) {
      expect(row(w, graph.graph_id).get('[data-testid="party-lineage-tab__row-name"]').text()).toBe(rootsJoined(graph));
      expect(row(w, graph.graph_id).get('[data-testid="party-lineage-tab__count"]').text()).toBe(`${graph.owned_count} / ${graph.total_count}`);
    }
  });

  it("draws one diamond per node in the node's state, the same way for one, few or seven nodes", () => {
    const w = mountTab();
    const layoutOf = (id) => [...row(w, id).element.querySelectorAll("*")].map((el) => el.className).filter((c) => !c.includes("pip") && !c.includes("tag"));
    for (const graph of [LINEAGE_HOLY_WATER_GRAPH, LINEAGE_STAFF_GRAPH, ICE]) {
      const pips = row(w, graph.graph_id).findAll('[data-testid="party-lineage-tab__pip"]');
      expect(pips.map((p) => p.attributes("data-state"))).toEqual(graph.nodes.map(nodeState));
      expect(pips.filter((p) => p.attributes("data-state") !== "locked")).toHaveLength(graph.owned_count);
      expect(layoutOf(graph.graph_id)).toEqual(layoutOf(ICE.graph_id));
    }
    // The single-node graph: one filled diamond and 1 / 1.
    const single = row(w, LINEAGE_HOLY_WATER_GRAPH.graph_id);
    expect(single.findAll('[data-testid="party-lineage-tab__pip"]').map((p) => p.attributes("data-state"))).toEqual(["capped"]);
    // The option's own text carries the state summary (its children are
    // presentational, so the diamonds themselves are hidden).
    expect(single.get('[data-testid="party-lineage-tab__state-summary"]').text()).toBe("（見頂 1）");
    expect(single.get('[data-testid="party-lineage-tab__pips"]').attributes("aria-hidden")).toBe("true");
  });

  it("marks 可解鎖 only on graphs with a ready node and 已全數見頂 only on consumed graphs", () => {
    const w = mountTab();
    for (const graph of PANEL.graphs) {
      expect(row(w, graph.graph_id).find('[data-testid="party-lineage-tab__ready"]').exists()).toBe(graph.nodes.some((n) => n.ready));
      expect(row(w, graph.graph_id).find('[data-testid="party-lineage-tab__consumed"]').exists()).toBe(graph.consumed);
    }
  });

  it("draws the selected graph by depth with the merge node once and its two labelled edges", () => {
    const w = mountTab();
    expect(w.get('[data-testid="party-lineage-tab__title"]').text()).toBe(rootsJoined(ICE));
    expect(w.findAll('[data-testid="party-lineage-tab__node"]')).toHaveLength(ICE.nodes.length);
    expect(w.findAll(`[data-testid="party-lineage-tab__node"][data-key="${MERGE_KEY}"]`)).toHaveLength(1);
    const incoming = w.findAll(`[data-testid="party-lineage-tab__edge-label"][data-to="${MERGE_KEY}"]`);
    expect(incoming.map((el) => el.text())).toEqual(ICE.edges.filter((e) => e.to_key === MERGE_KEY).map((e) => `Lv ${e.min_level}`));
    expect(incoming).toHaveLength(2);
    expect(w.findAll(`[data-testid="party-lineage-tab__edge"][data-to="${MERGE_KEY}"]`)).toHaveLength(2);
    expect(w.findAll('[data-testid="party-lineage-tab__edge-label"]')).toHaveLength(ICE.edges.length);
    expect(w.get('[data-testid="party-lineage-tab__canvas"]').attributes("data-rows")).toBe(String(graphLayout(ICE).rows));
  });

  it("tells the node states apart by text as well as style", () => {
    const w = mountTab();
    expect(node(w, CAPPED_ROOT.skill_key).attributes("data-state")).toBe("capped");
    expect(node(w, CAPPED_ROOT.skill_key).get('[data-testid="party-lineage-tab__node-growth"]').text()).toBe("見頂");
    const band = OWNED_ROOT.xp_into_level + OWNED_ROOT.xp_to_next_level;
    expect(node(w, OWNED_ROOT.skill_key).get('[data-testid="party-lineage-tab__node-meter"]').text()).toBe(`${OWNED_ROOT.xp_into_level}/${band} → 下一階`);
    expect(node(w, OWNED_ROOT.skill_key).text()).toContain(`Lv ${OWNED_ROOT.level}`);
    expect(node(w, LOCKED.skill_key).attributes("data-state")).toBe("locked");
    expect(node(w, LOCKED.skill_key).get('[data-testid="party-lineage-tab__node-prereq"]').text()).toBe(LOCKED.prereq_text_zh);
    expect(node(w, READY.skill_key).get('[data-testid="party-lineage-tab__node-ready"]').text()).toBe("可解鎖");
    expect(node(w, READY.skill_key).find('[data-testid="party-lineage-tab__node-prereq"]').exists()).toBe(false);
    // No chain meter, and no growth line on a node not owned.
    expect(node(w, LOCKED.skill_key).find('[data-testid="party-lineage-tab__node-growth"]').exists()).toBe(false);
  });

  it("opens an owned node's skill and never a locked one, nor any while a member switch is in flight", async () => {
    const w = mountTab();
    await node(w, OWNED_ROOT.skill_key).trigger("click");
    expect(w.emitted("open-skill")).toEqual([[OWNED_ROOT.skill_key]]);
    await node(w, LOCKED.skill_key).trigger("click");
    await node(w, READY.skill_key).trigger("click");
    expect(node(w, LOCKED.skill_key).attributes("aria-disabled")).toBe("true");
    expect(w.emitted("open-skill")).toHaveLength(1);
    await w.setProps({ pending: true });
    await node(w, OWNED_ROOT.skill_key).trigger("click");
    expect(node(w, OWNED_ROOT.skill_key).attributes("aria-disabled")).toBe("true");
    expect(w.emitted("open-skill")).toHaveLength(1);
  });

  it("selects a row on click and moves focus with the arrow keys", async () => {
    const w = mountTab();
    expect(row(w, ICE.graph_id).attributes("aria-selected")).toBe("true");
    await row(w, LINEAGE_HOLY_WATER_GRAPH.graph_id).trigger("click");
    expect(w.get('[data-testid="party-lineage-tab__title"]').text()).toBe(rootsJoined(LINEAGE_HOLY_WATER_GRAPH));
    expect(w.get('[data-testid="party-lineage-tab__detail-consumed"]').text()).toBe("已全數見頂");
    row(w, LINEAGE_HOLY_WATER_GRAPH.graph_id).element.focus();
    await row(w, LINEAGE_HOLY_WATER_GRAPH.graph_id).trigger("keydown", { key: "ArrowDown" });
    expect(document.activeElement).toBe(row(w, LINEAGE_STAFF_GRAPH.graph_id).element);
    await row(w, LINEAGE_STAFF_GRAPH.graph_id).trigger("keydown", { key: "Home" });
    expect(document.activeElement).toBe(row(w, ICE.graph_id).element);
  });

  it("opens the linked skill's graph and marks its node", () => {
    const w = mountTab({ focusSkill: LINEAGE_PRAYER_GRAPH.nodes[1].skill_key });
    expect(row(w, LINEAGE_PRAYER_GRAPH.graph_id).attributes("aria-selected")).toBe("true");
    expect(node(w, LINEAGE_PRAYER_GRAPH.nodes[1].skill_key).attributes("aria-current")).toBe("true");
  });

  it("keeps the selection across a republish and falls back when its graph leaves", async () => {
    const w = mountTab({ initialGraph: LINEAGE_STAFF_GRAPH.graph_id });
    await w.setProps({ lineage: { ...PANEL, graphs: [...PANEL.graphs] } });
    expect(row(w, LINEAGE_STAFF_GRAPH.graph_id).attributes("aria-selected")).toBe("true");
    await w.setProps({ lineage: { ...PANEL, graphs: PANEL.graphs.filter((g) => g !== LINEAGE_STAFF_GRAPH) } });
    expect(row(w, ICE.graph_id).attributes("aria-selected")).toBe("true");
  });

  it("finds the linked graph in a payload committed after the tab opened", async () => {
    const w = mountTab({ lineage: LINEAGE_UNAVAILABLE_SAMPLE, focusSkill: LINEAGE_STAFF_GRAPH.nodes[0].skill_key });
    await w.setProps({ lineage: PANEL });
    expect(row(w, LINEAGE_STAFF_GRAPH.graph_id).attributes("aria-selected")).toBe("true");
    expect(node(w, LINEAGE_STAFF_GRAPH.nodes[0].skill_key).attributes("aria-current")).toBe("true");
  });

  it("chooses again for a new member, also when that member's payload lands later", async () => {
    const other = PARTY_WINDOW_PANEL_SAMPLE.slots.find((r) => r.identity !== MEMBER.identity);
    const next = { ...PANEL, graphs: [LINEAGE_STAFF_GRAPH, ICE] };
    // The rail flips first; the old payload is still committed.
    const w = mountTab({ initialGraph: LINEAGE_PRAYER_GRAPH.graph_id });
    await w.setProps({ member: other });
    await w.setProps({ lineage: next });
    expect(row(w, LINEAGE_STAFF_GRAPH.graph_id).attributes("aria-selected")).toBe("true");
    // The player's own choice then survives a republish for the same member.
    await row(w, ICE.graph_id).trigger("click");
    await w.setProps({ lineage: { ...next, graphs: [...next.graphs] } });
    expect(row(w, ICE.graph_id).attributes("aria-selected")).toBe("true");
    // Rail and payload in one update: the new payload's first graph, kept afterwards.
    await w.setProps({ member: MEMBER, lineage: PANEL });
    expect(row(w, ICE.graph_id).attributes("aria-selected")).toBe("true");
    await row(w, LINEAGE_HOLY_WATER_GRAPH.graph_id).trigger("click");
    await w.setProps({ lineage: { ...PANEL, graphs: [...PANEL.graphs] } });
    expect(row(w, LINEAGE_HOLY_WATER_GRAPH.graph_id).attributes("aria-selected")).toBe("true");
  });

  it("states an unavailable panel's reason and invents no graph", () => {
    const w = mountTab({ lineage: LINEAGE_UNAVAILABLE_SAMPLE });
    expect(w.get('[data-testid="party-window__tab-unavailable"]').text()).toBe(LINEAGE_UNAVAILABLE_SAMPLE.reason.message);
    expect(w.find('[data-testid="party-lineage-tab__row"]').exists()).toBe(false);
    expect(w.find('[data-testid="party-lineage-tab__detail"]').exists()).toBe(false);
    expect(w.find('[data-testid="party-lineage-tab__summary"]').exists()).toBe(false);
  });

  it("renders only the payload's graphs: none when empty or never committed", () => {
    let w = mountTab({ lineage: LINEAGE_EMPTY_SAMPLE });
    expect(w.get('[data-testid="party-lineage-tab__empty"]').exists()).toBe(true);
    expect(w.find('[data-testid="party-lineage-tab__detail"]').exists()).toBe(false);
    w.unmount();
    w = mountTab({ lineage: null });
    expect(w.get('[data-testid="list-detail__list"]').text()).toBe("");
    w.unmount();
    // A truncated payload (one graph omitted) draws exactly what remains.
    w = mountTab({ lineage: { ...PANEL, graphs: [ICE] } });
    expect(w.findAll('[data-testid="party-lineage-tab__row"]')).toHaveLength(1);
  });
});

describe("PartySkillTab focusSkill (the 系譜 link target)", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  const selectedRow = (w) => w.find('[data-testid="party-skill-tab__row"][aria-selected="true"]');

  it("selects the focused active skill ahead of the committed selection and asks the server", async () => {
    const requestSkill = vi.fn(() => 1);
    wrapper = mount(PartySkillTab, { attachTo: document.body, props: { member: MEMBER, character: CHARACTER, requestSkill, focusSkill: OWNED_ROOT.skill_key } });
    await nextTick();
    expect(selectedRow(wrapper).attributes("data-key")).toBe(OWNED_ROOT.skill_key);
    expect(requestSkill).toHaveBeenCalledWith({ member_id: CHARACTER.member_id, skill_key: OWNED_ROOT.skill_key });
  });

  it("switches to the passive segment for a passive skill", async () => {
    const passive = CHARACTER.passives[0].groups[0].skills[0].key;
    wrapper = mount(PartySkillTab, { attachTo: document.body, props: { member: MEMBER, character: CHARACTER, requestSkill: () => 1, focusSkill: passive } });
    await nextTick();
    expect(wrapper.get('[data-testid="party-skill-tab__segment--passive"]').attributes("aria-pressed")).toBe("true");
    expect(selectedRow(wrapper).attributes("data-key")).toBe(passive);
  });

  it("falls back to the committed selection for a key the payload lacks", async () => {
    wrapper = mount(PartySkillTab, { attachTo: document.body, props: { member: MEMBER, character: CHARACTER, requestSkill: () => 1, focusSkill: "absent_skill" } });
    await nextTick();
    expect(selectedRow(wrapper).attributes("data-key")).toBe(CHARACTER.selected_skill.key);
  });

  it("waits for a payload committed after the tab opened", async () => {
    wrapper = mount(PartySkillTab, { attachTo: document.body, props: { member: MEMBER, character: null, requestSkill: () => 1, focusSkill: OWNED_ROOT.skill_key } });
    await wrapper.setProps({ character: CHARACTER });
    await nextTick();
    expect(selectedRow(wrapper).attributes("data-key")).toBe(OWNED_ROOT.skill_key);
  });

  it("drops the wish once the player switches segment", async () => {
    wrapper = mount(PartySkillTab, { attachTo: document.body, props: { member: MEMBER, character: null, requestSkill: () => 1, focusSkill: OWNED_ROOT.skill_key } });
    await wrapper.setProps({ character: { ...CHARACTER, actives: [] } });
    await wrapper.get('[data-testid="party-skill-tab__segment--passive"]').trigger("click");
    await wrapper.setProps({ character: CHARACTER });
    await nextTick();
    expect(wrapper.get('[data-testid="party-skill-tab__segment--passive"]').attributes("aria-pressed")).toBe("true");
  });

  it("keeps the wish through a transiently unavailable payload", async () => {
    wrapper = mount(PartySkillTab, { attachTo: document.body, props: { member: MEMBER, character: { ...CHARACTER, actives: [] }, requestSkill: () => 1, focusSkill: OWNED_ROOT.skill_key } });
    await wrapper.setProps({ character: { schema_version: CHARACTER.schema_version, available: false, reason: { code: "x", message: "x" } } });
    await wrapper.setProps({ character: CHARACTER });
    await nextTick();
    expect(selectedRow(wrapper).attributes("data-key")).toBe(OWNED_ROOT.skill_key);
  });

  it("keeps a refused selection local and retries it when the lock opens", async () => {
    const requestSkill = vi.fn(() => 1);
    wrapper = mount(PartySkillTab, { attachTo: document.body, props: { member: MEMBER, character: CHARACTER, requestSkill, useLocked: true, focusSkill: OWNED_ROOT.skill_key } });
    await nextTick();
    expect(selectedRow(wrapper).attributes("data-key")).toBe(OWNED_ROOT.skill_key);
    expect(requestSkill).not.toHaveBeenCalled();
    await wrapper.setProps({ useLocked: false });
    await nextTick();
    expect(requestSkill).toHaveBeenCalledTimes(1);
    expect(requestSkill).toHaveBeenCalledWith({ member_id: CHARACTER.member_id, skill_key: OWNED_ROOT.skill_key });
  });
});

describe("PartyWindow 系譜 ↔ 技能 links", () => {
  let wrapper;
  const SCOPE = "test|lineage";

  beforeEach(() => {
    resetPartyWindowMemory();
  });
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountWindow(tab, props = {}) {
    rememberPartyWindowTab(SCOPE, tab);
    wrapper = mount(PartyWindow, {
      attachTo: document.body,
      props: { party: PARTY_WINDOW_PANEL_SAMPLE, character: CHARACTER, lineage: PANEL, memoryScope: SCOPE, requestSkill: vi.fn(() => 1), ...props },
    });
    return wrapper;
  }
  const dataTab = () => wrapper.get('[data-testid="party-window"]').attributes("data-tab");
  const tabButton = (key) => wrapper.get(`[data-testid="icon-tabs__tab--${key}"]`);
  const selectedSkill = () => wrapper.get('[data-testid="party-skill-tab__row"][aria-selected="true"]').attributes("data-key");

  it("activating a node switches to 技能 with that skill selected and dispatches its selection", async () => {
    const requestSkill = vi.fn(() => 1);
    mountWindow("lineage", { requestSkill });
    await wrapper.get(`[data-testid="party-lineage-tab__node"][data-key="${OWNED_ROOT.skill_key}"]`).trigger("click");
    await nextTick();
    expect(dataTab()).toBe("skills");
    expect(selectedSkill()).toBe(OWNED_ROOT.skill_key);
    expect(requestSkill).toHaveBeenCalledWith({ member_id: CHARACTER.member_id, skill_key: OWNED_ROOT.skill_key });
    expect(wrapper.emitted("view-member")).toBeUndefined();
  });

  it("a plain tab switch afterwards applies no stale link", async () => {
    mountWindow("lineage");
    await wrapper.get(`[data-testid="party-lineage-tab__node"][data-key="${OWNED_ROOT.skill_key}"]`).trigger("click");
    await nextTick();
    await tabButton("lineage").trigger("click");
    await tabButton("skills").trigger("click");
    await nextTick();
    expect(selectedSkill()).toBe(CHARACTER.selected_skill.key);
  });

  it("the 技能 tab's link opens the selected skill's graph with its node marked", async () => {
    mountWindow("skills");
    await nextTick();
    await wrapper.get('[data-testid="party-skill-tab__lineage-link"]').trigger("click");
    await nextTick();
    expect(dataTab()).toBe("lineage");
    expect(wrapper.get(`[data-testid="party-lineage-tab__row"][data-graph="${LINEAGE_PRAYER_GRAPH.graph_id}"]`).attributes("aria-selected")).toBe("true");
    expect(wrapper.get(`[data-testid="party-lineage-tab__node"][data-key="${CHARACTER.selected_skill.key}"]`).attributes("aria-current")).toBe("true");
  });

  it("disables node activation while a rail selection is in flight", async () => {
    mountWindow("lineage", { pendingMemberId: 102 });
    await wrapper.get(`[data-testid="party-lineage-tab__node"][data-key="${OWNED_ROOT.skill_key}"]`).trigger("click");
    expect(dataTab()).toBe("lineage");
  });
});
