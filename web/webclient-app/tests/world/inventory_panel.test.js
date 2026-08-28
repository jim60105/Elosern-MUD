import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import InventoryPanel from "../../components/InventoryPanel.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_PRESENTATION_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

const CHARACTER_UNAVAILABLE = {
  schema_version: 4,
  available: false,
  kind: "character",
  reason: { code: "no_puppet", message: "你已離開角色" },
};

describe("InventoryPanel (redesign-inventory-item-grid: the held-item tile grid)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountPanel(props = {}) {
    // Attach to a host in the document so `.focus()` updates
    // `document.activeElement` (the drawer's focus-trap contract relies on it).
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(InventoryPanel, {
      attachTo: host,
      props: {
        services: SERVICES_PANEL_SAMPLE,
        character: CHARACTER_PANEL_SAMPLE,
        // The drawer-layer wallet figure `AppClient` would pass (the same
        // validated `character` panel integer the head subtitle renders).
        wallet: CHARACTER_PANEL_SAMPLE.wallet,
        ...props,
      },
    });
    return wrapper;
  }

  function ceilingServices() {
    const rows = Array.from({ length: 32 }, (_, i) => ({
      item_key: `item_ceiling_${i + 1}`,
      display_name: `物品 ${i + 1}`,
      held: 1,
      equipped: i < 3,
      presentation: null,
    }));
    return {
      ...SERVICES_PANEL_SAMPLE,
      inventory: { rows, wallet: 3240 },
      pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 32 },
    };
  }

  it("renders every committed row as a native-button tile with a lower-corner held count", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const tiles = w.findAll('[data-testid^="inventory-panel__tile--"]');
    expect(tiles).toHaveLength(9);
    for (const tile of tiles) {
      const key = tile.element.dataset.key;
      const count = w.get(`[data-testid="inventory-panel__count--${key}"]`).text();
      const row = SERVICES_PANEL_PRESENTATION_SAMPLE.inventory.rows.find((r) => r.item_key === key);
      expect(count).toBe(String(row.held));
      expect(tile.element.tagName.toLowerCase()).toBe("button");
    }
  });

  it("renders the equipped check marker only on equipped rows (non-colour state)", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    // Three equipped rows (plain_sword, leather_armor, mist_amulet).
    expect(w.get('[data-testid="inventory-panel__equipped--plain_sword"]').exists()).toBe(true);
    expect(w.get('[data-testid="inventory-panel__equipped--leather_armor"]').exists()).toBe(true);
    expect(w.get('[data-testid="inventory-panel__equipped--mist_amulet"]').exists()).toBe(true);
    expect(w.find('[data-testid="inventory-panel__equipped--healing_potion"]').exists()).toBe(false);
  });

  it("drives the per-rarity border treatment from committed row metadata", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    expect(w.get('[data-testid="inventory-panel__tile--meal"]').attributes("data-rarity")).toBe("common");
    expect(w.get('[data-testid="inventory-panel__tile--leather_armor"]').attributes("data-rarity")).toBe("uncommon");
    expect(w.get('[data-testid="inventory-panel__tile--healing_potion"]').attributes("data-rarity")).toBe("rare");
    expect(w.get('[data-testid="inventory-panel__tile--mist_amulet"]').attributes("data-rarity")).toBe("epic");
    expect(w.get('[data-testid="inventory-panel__tile--travel_pack"]').attributes("data-rarity")).toBe("legendary");
  });

  it("renders the neutral unknown-item tile for presentation: null without inference", () => {
    const w = mountPanel();
    const tile = w.get('[data-testid="inventory-panel__tile--item_iron_sword"]');
    expect(tile.attributes("data-rarity")).toBe("unknown");
    expect(tile.attributes("data-unknown")).toBe("true");
    // The unknown marker, the real name, and the held count render; no kind,
    // rarity, or summary is invented from the item key or display name.
    expect(w.get('[data-testid="inventory-panel__unknown--item_iron_sword"]').text()).toBe("未知");
    expect(w.get('[data-testid="inventory-panel__name--item_iron_sword"]').text()).toBe("鐵劍");
    expect(w.get('[data-testid="inventory-panel__count--item_iron_sword"]').text()).toBe("1");
  });

  it("shows the inspector with the identical committed content for hover and focus", async () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const potionTile = w.get('[data-testid="inventory-panel__tile--healing_potion"]');
    const row = SERVICES_PANEL_PRESENTATION_SAMPLE.inventory.rows.find((r) => r.item_key === "healing_potion");

    // Pointer hover path.
    potionTile.trigger("pointerenter");
    await nextTick();
    const inspector = w.get('[data-testid="inventory-panel__inspector"]');
    const hoverContent = {
      name: w.get('[data-testid="inventory-panel__inspector-name"]').text(),
      rarity: w.get('[data-testid="inventory-panel__inspector-rarity"]').text(),
      kind: w.get('[data-testid="inventory-panel__inspector-kind"]').text(),
      summary: w.get('[data-testid="inventory-panel__inspector-summary"]').text(),
      held: w.get('[data-testid="inventory-panel__inspector-held"]').text(),
      equipped: w.get('[data-testid="inventory-panel__inspector-equipped"]').text(),
    };
    expect(hoverContent).toEqual({
      name: row.display_name,
      rarity: "稀有",
      kind: "藥水",
      summary: row.presentation.summary,
      held: String(row.held),
      equipped: "未裝備",
    });

    // Pointer leave with focus elsewhere clears the inspector.
    potionTile.trigger("pointerleave");
    await nextTick();
    expect(w.find('[data-testid="inventory-panel__inspector"]').exists()).toBe(false);

    // Keyboard focus path: the same committed content renders again.
    potionTile.element.focus();
    await nextTick();
    const focusContent = {
      name: w.get('[data-testid="inventory-panel__inspector-name"]').text(),
      rarity: w.get('[data-testid="inventory-panel__inspector-rarity"]').text(),
      kind: w.get('[data-testid="inventory-panel__inspector-kind"]').text(),
      summary: w.get('[data-testid="inventory-panel__inspector-summary"]').text(),
      held: w.get('[data-testid="inventory-panel__inspector-held"]').text(),
      equipped: w.get('[data-testid="inventory-panel__inspector-equipped"]').text(),
    };
    expect(focusContent).toEqual(hoverContent);
  });

  it("links the selected tile to the inspector via aria-describedby and clears it when absent", async () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const potionTile = w.get('[data-testid="inventory-panel__tile--healing_potion"]');
    expect(potionTile.attributes("aria-describedby")).toBeUndefined();
    potionTile.element.focus();
    await nextTick();
    expect(potionTile.attributes("aria-describedby")).toBe("inventory-panel-inspector");
    // Blur to a non-tile element: the inspector hides and the link clears.
    const other = document.createElement("button");
    document.body.appendChild(other);
    other.focus();
    await nextTick();
    expect(w.find('[data-testid="inventory-panel__inspector"]').exists()).toBe(false);
    expect(potionTile.attributes("aria-describedby")).toBeUndefined();
  });

  it("offers no state-changing control (no use/consume/equip/drag/sort/filter/search)", async () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    // The only buttons are the item tiles themselves; no input or select.
    const buttons = w.findAll("button");
    expect(buttons).toHaveLength(9);
    expect(w.find("input").exists()).toBe(false);
    expect(w.find("select").exists()).toBe(false);
    // The inspector is non-interactive: no control lives inside it.
    w.get('[data-testid="inventory-panel__tile--healing_potion"]').element.focus();
    await nextTick();
    const inspector = w.get('[data-testid="inventory-panel__inspector"]');
    expect(inspector.find("button").exists()).toBe(false);
    expect(inspector.find("input").exists()).toBe(false);
    expect(inspector.attributes("role")).toBe("tooltip");
  });

  it("resets the local selection when the committed panel data is replaced", async () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const potionTile = w.get('[data-testid="inventory-panel__tile--healing_potion"]');
    potionTile.element.focus();
    await nextTick();
    expect(w.find('[data-testid="inventory-panel__inspector"]').exists()).toBe(true);
    // Replace the panel with a payload that no longer contains the focused row.
    await w.setProps({ services: SERVICES_PANEL_SAMPLE });
    await nextTick();
    expect(w.find('[data-testid="inventory-panel__inspector"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__tile--healing_potion"]').exists()).toBe(true);
    expect(w.find('[data-testid="inventory-panel__tile--item_heal_potion"]').exists()).toBe(true);
  });

  it("states the 32-row ceiling in words only at the bound; no total otherwise", () => {
    const w = mountPanel();
    expect(w.find('[data-testid="inventory-panel__ceiling"]').exists()).toBe(false);
    const wCeiling = mountPanel({ services: ceilingServices() });
    const ceiling = wCeiling.get('[data-testid="inventory-panel__ceiling"]');
    expect(ceiling.exists()).toBe(true);
    expect(ceiling.text()).toContain("32");
    expect(wCeiling.findAll('[data-testid^="inventory-panel__tile--"]').length).toBe(32);
  });

  it("section absent: renders the registry-owned absence message, no invented bag contents", () => {
    const w = mountPanel({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    const absent = w.get('[data-testid="inventory-panel__absent"]');
    expect(absent.text()).toBe("背包目前是空的。");
    expect(w.find('[data-testid^="inventory-panel__tile--"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__ceiling"]').exists()).toBe(false);
  });

  it("unavailable services: renders only the registry-owned reason, no fabricated wallet, row or slot", () => {
    const w = mountPanel({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
    const reason = w.get('[data-testid="inventory-panel__unavailable"]');
    expect(reason.text()).toBe("服務選單目前無法顯示");
    expect(w.find('[data-testid="inventory-panel__absent"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__ceiling"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="inventory-panel__tile--"]').length).toBe(0);
  });

  it("composes the equipment doll before the held-item grid", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const doll = w.get('[data-testid="equipment-doll"]').element;
    const grid = w.get('[data-testid="inventory-panel__grid"]').element;
    const pos = doll.compareDocumentPosition(grid);
    expect(pos & Node.DOCUMENT_POSITION_FOLLOWING).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    // The committed name reads in the doll's 裝備描述 column, not the cell.
    expect(w.get('[data-testid="equipment-doll__description-row--weapon_main"]').text()).toContain("短劍 · 拾遺");
  });

  it("stacks the mock's 裝備 / 物品 / 金錢 sections on the bare drawer body", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const doll = w.get('[data-testid="equipment-doll"]').element;
    const items = w.get('[data-testid="inventory-panel__section--items"]').element;
    const wallet = w.get('[data-testid="inventory-panel__section--wallet"]').element;
    const following = (a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) === Node.DOCUMENT_POSITION_FOLLOWING;
    expect(following(doll, items)).toBe(true);
    expect(following(items, wallet)).toBe(true);
    // The 物品 heading is tagged with the shipped listing size (the fixture
    // carries 9 rows) — never a claim of the player's total holdings.
    expect(w.get('[data-testid="inventory-panel__items-count"]').text()).toBe("9");
    // No panel-card wrapper: the body paints no `--panel` background of its
    // own (the sections sit directly on the transparent drawer body).
    const source = readFileSync(
      join(process.cwd(), "web/webclient-app/components/InventoryPanel.vue"),
      "utf-8",
    );
    expect(source).not.toContain("background: var(--panel);");
    expect(source).not.toContain("border-radius: var(--radius);");
  });

  it("renders the 金錢 section row with the grouped integer copper wallet", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE, wallet: 1284000 });
    expect(w.get('[data-testid="inventory-panel__section--wallet"]').text()).toContain("金錢");
    expect(w.get('[data-testid="inventory-panel__wallet-value"]').text()).toBe("1,284,000");
    expect(w.get(".inventory-panel__statrow-label").text()).toContain("錢袋");
    expect(w.get(".inventory-panel__statrow-unit").text()).toBe("整數銅");
    // A committed zero is a committed figure: it renders (nothing is
    // fabricated only when no committed figure exists — next test).
    const wZero = mountPanel({ wallet: 0 });
    expect(wZero.get('[data-testid="inventory-panel__wallet-value"]').text()).toBe("0");
  });

  it("renders no 金錢 row (and no balance) without a committed integer wallet", () => {
    for (const wallet of [null, 12.5, -1, Number.NaN]) {
      const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE, wallet });
      expect(w.find('[data-testid="inventory-panel__section--wallet"]').exists(), String(wallet)).toBe(false);
    }
    // Unavailable services / absent section: the bag fabricates no wallet,
    // no `物品` heading section, and no `金錢` row.
    const wUnavailable = mountPanel({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE, wallet: 3240 });
    expect(wUnavailable.find('[data-testid="inventory-panel__section--wallet"]').exists()).toBe(false);
    expect(wUnavailable.find('[data-testid="inventory-panel__section--items"]').exists()).toBe(false);
    const wAbsent = mountPanel({ services: SERVICES_PANEL_MINIMAL_SAMPLE, wallet: 3240 });
    expect(wAbsent.find('[data-testid="inventory-panel__section--wallet"]').exists()).toBe(false);
    expect(wAbsent.find('[data-testid="inventory-panel__section--items"]').exists()).toBe(false);
  });

  it("never reproduces the mock's 排序/篩選/找尋 pills", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const text = w.text();
    expect(text).not.toContain("排序");
    expect(text).not.toContain("篩選");
    expect(text).not.toContain("找尋");
  });

  it("renders no equipment doll when the character panel is unavailable; the held grid remains", () => {
    const w = mountPanel({ character: CHARACTER_UNAVAILABLE, services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    expect(w.findAll('[data-testid^="inventory-panel__tile--"]').length).toBe(9);
    expect(w.get('[data-testid="equipment-doll__unavailable"]').text()).toBe("你已離開角色");
  });

  it("renders no doll (and no fabricated empty slots) when the character panel is missing", () => {
    const w = mountPanel({ character: null, services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    expect(w.findAll('[data-testid^="inventory-panel__tile--"]').length).toBe(9);
    expect(w.find('[data-testid="equipment-doll"]').exists()).toBe(false);
  });

  it("gates its transitions through the motion tokens (reduced motion is instant)", () => {
    // The cell outline and inspector transitions/animation use the existing
    // `--motion-fast` token; the reduced-motion override sets the token to
    // 1ms, making every transition effectively instant.
    const source = readFileSync(
      join(process.cwd(), "web/webclient-app/components/InventoryPanel.vue"),
      "utf-8",
    );
    expect(source).toContain("var(--motion-fast)");
    expect(source).toContain("var(--ease-standard)");
    expect(source).toContain("inventory-inspector-in");
  });
});

// add-inventory-item-actions (task 6.4): deliberate activation follows the
// committed action descriptor — inspect/disabled dispatch nothing, an
// enabled use opens the labelled confirmation, an enabled toggle dispatches
// immediately, and every intent emits exactly once to the parent.
function servicesWithActions() {
  const useAction = (enabled, reason = null) => ({
    action_id: "inventory.use",
    label: "使用",
    enabled,
    disabled_reason: enabled ? null : reason,
    quantity: null,
  });
  const toggleAction = (label) => ({
    action_id: "inventory.toggle_equip",
    label,
    enabled: true,
    disabled_reason: null,
    quantity: null,
  });
  const row = (item_key, display_name, action, equipped = false) => ({
    item_key,
    display_name,
    held: 2,
    equipped,
    presentation: { kind: "potion", icon_key: "potion", summary: "恢復體力。", rarity: "common" },
    action,
  });
  return {
    ...SERVICES_PANEL_SAMPLE,
    inventory: {
      rows: [
        row("potion_use", "治療藥水", useAction(true)),
        row("potion_full", "過剩藥水", useAction(false, { code: "hp_full", message: "你的體力已滿。" })),
        row("sword_toggle", "鐵劍", toggleAction("裝備"), true),
        row("mystery", "未知物品", null),
      ],
      wallet: 3240,
    },
  };
}

describe("InventoryPanel row actions (add-inventory-item-actions)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountActions() {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(InventoryPanel, {
      attachTo: host,
      props: {
        services: servicesWithActions(),
        character: CHARACTER_PANEL_SAMPLE,
        wallet: CHARACTER_PANEL_SAMPLE.wallet,
      },
    });
    return wrapper;
  }

  function bodyByTestId(id) {
    return document.querySelector(`[data-testid="${id}"]`);
  }

  it("an enabled inventory.use opens the confirmation and dispatches only on confirm, exactly once", async () => {
    const w = mountActions();
    const tile = w.get('[data-testid="inventory-panel__tile--potion_use"]');
    await tile.trigger("click");
    expect(w.emitted("use")).toBeUndefined();
    const dialog = bodyByTestId("inventory-panel__confirm-dialog");
    expect(dialog).not.toBeNull();
    expect(dialog.getAttribute("role")).toBe("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(dialog.getAttribute("aria-label")).toContain("治療藥水");
    expect(bodyByTestId("inventory-panel__confirm-text").textContent).toContain("治療藥水");
    // Focus enters the dialog on the confirm control.
    expect(document.activeElement).toBe(bodyByTestId("inventory-panel__confirm-ok"));
    bodyByTestId("inventory-panel__confirm-ok").click();
    await nextTick();
    expect(w.emitted("use")).toEqual([
      [{ action_id: "inventory.use", payload: { item_key: "potion_use" } }],
    ]);
    expect(bodyByTestId("inventory-panel__confirm-dialog")).toBeNull();
  });

  it("cancel, backdrop, and Escape dispatch nothing and restore focus to the originating tile", async () => {
    for (const close of ["cancel", "backdrop", "escape"]) {
      const w = mountActions();
      const tile = w.get('[data-testid="inventory-panel__tile--potion_use"]');
      await tile.trigger("click");
      if (close === "cancel") {
        bodyByTestId("inventory-panel__confirm-cancel").click();
      } else if (close === "backdrop") {
        bodyByTestId("inventory-panel__confirm-backdrop").click();
      } else {
        bodyByTestId("inventory-panel__confirm").dispatchEvent(
          new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
        );
      }
      await nextTick();
      expect(w.emitted("use")).toBeUndefined();
      expect(w.emitted("toggle-equip")).toBeUndefined();
      expect(bodyByTestId("inventory-panel__confirm-dialog")).toBeNull();
      expect(document.activeElement).toBe(tile.element);
      w.unmount();
      wrapper = null;
      document.body.innerHTML = "";
    }
  });

  it("a committed panel replacement retires an open confirmation without dispatching", async () => {
    const w = mountActions();
    await w.get('[data-testid="inventory-panel__tile--potion_use"]').trigger("click");
    expect(bodyByTestId("inventory-panel__confirm-dialog")).not.toBeNull();
    await w.setProps({ services: { ...servicesWithActions() } });
    expect(bodyByTestId("inventory-panel__confirm-dialog")).toBeNull();
    expect(w.emitted("use")).toBeUndefined();
  });

  it("the confirmation trap keeps Tab within the dialog controls", async () => {
    const w = mountActions();
    await w.get('[data-testid="inventory-panel__tile--potion_use"]').trigger("click");
    const ok = bodyByTestId("inventory-panel__confirm-ok");
    expect(document.activeElement).toBe(ok);
    ok.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
    expect(document.activeElement).toBe(bodyByTestId("inventory-panel__confirm-cancel"));
  });

  it("an enabled inventory.toggle_equip dispatches immediately, once, without confirmation", async () => {
    const w = mountActions();
    await w.get('[data-testid="inventory-panel__tile--sword_toggle"]').trigger("click");
    expect(w.emitted("toggle-equip")).toEqual([
      [{ action_id: "inventory.toggle_equip", payload: { item_key: "sword_toggle" } }],
    ]);
    expect(w.emitted("use")).toBeUndefined();
    expect(bodyByTestId("inventory-panel__confirm-dialog")).toBeNull();
  });

  it("a disabled action is aria-disabled, spells the committed reason, and dispatches nothing", async () => {
    const w = mountActions();
    const tile = w.get('[data-testid="inventory-panel__tile--potion_full"]');
    expect(tile.attributes("aria-disabled")).toBe("true");
    await tile.trigger("click");
    expect(w.emitted("use")).toBeUndefined();
    expect(w.emitted("toggle-equip")).toBeUndefined();
    expect(bodyByTestId("inventory-panel__confirm-dialog")).toBeNull();
    // The shared inspector still presents the row and spells the bounded reason.
    expect(bodyByTestId("inventory-panel__inspector")).not.toBeNull();
    expect(bodyByTestId("inventory-panel__inspector-reason").textContent).toContain("你的體力已滿。");
  });

  it("an inspect-only (null action) tile selects and dispatches nothing", async () => {
    const w = mountActions();
    await w.get('[data-testid="inventory-panel__tile--mystery"]').trigger("click");
    expect(w.emitted("use")).toBeUndefined();
    expect(w.emitted("toggle-equip")).toBeUndefined();
    expect(bodyByTestId("inventory-panel__confirm-dialog")).toBeNull();
  });
});
