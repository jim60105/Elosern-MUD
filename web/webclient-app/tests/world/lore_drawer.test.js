import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LoreDrawer from "../../components/LoreDrawer.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("LoreDrawer (B4 services family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountDrawer(props = {}) {
    wrapper = mount(LoreDrawer, {
      props: {
        services: SERVICES_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the host line with display_name and identity", () => {
    const w = mountDrawer();
    expect(w.get('[data-testid="lore-drawer__host"]').text()).toContain("霧骨渡口的服務門戶");
    expect(w.get('[data-testid="lore-drawer__host-identity"]').text()).toBe("host_altoria");
  });

  it("omits the host block entirely in the minimal fixture (honest absence)", () => {
    const w = mountDrawer({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    expect(w.find('[data-testid="lore-drawer__host"]').exists()).toBe(false);
  });

  it("omits the player summary block entirely (H4 task 5.2: wallet/summary moved to CharacterStatusDrawer)", () => {
    const w = mountDrawer();
    expect(w.find('[data-testid="lore-drawer__summary"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__wallet"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__guild-register"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__rank"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__merit"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__next-rank"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__next-threshold"]').exists()).toBe(false);
  });

  it("renders no player fields the payload carries (honest absence after H4 task 5.2)", () => {
    const w = mountDrawer({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    expect(w.find('[data-testid="lore-drawer__wallet"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__guild-register"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__rank"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__next-rank"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__next-threshold"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__merit"]').exists()).toBe(false);
  });

  it("renders the guild lore: board summaries and the active quest detail", () => {
    const w = mountDrawer();
    const mill = w.get('[data-testid="lore-drawer__board-lore--quest_mill_grain"]');
    expect(mill.text()).toContain("將十袋糧食運往磨坊");
    expect(mill.text()).toContain("400 銅＋公會功績 25");
    const harbor = w.get('[data-testid="lore-drawer__board-lore--quest_harbor_light"]');
    expect(harbor.text()).toContain("為渡口燈塔補足燈油");
    expect(harbor.text()).toContain("220 銅＋公會功績 15");

    const questDetail = w.get('[data-testid="lore-drawer__quest-detail--q_1042"]');
    expect(questDetail.text()).toContain("磨坊糧運");
    expect(questDetail.text()).toContain("進行中");
    expect(questDetail.text()).toContain("老周把三袋糧食交給你，要求天亮前送到磨坊。");
  });

  it("shows the absent marker with zero invented lore lines in the minimal fixture", () => {
    const w = mountDrawer({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    expect(w.get('[data-testid="lore-drawer__absent"]').exists()).toBe(true);
    expect(w.text()).toContain("尚無公會圖鑑資料");
    expect(w.findAll('[data-testid^="lore-drawer__board-lore--"]')).toHaveLength(0);
    expect(w.findAll('[data-testid^="lore-drawer__quest-detail--"]')).toHaveLength(0);
  });

  it("labels a failed quest detail with the server bounded-state label", () => {
    const services = {
      ...SERVICES_PANEL_SAMPLE,
      guild: {
        ...SERVICES_PANEL_SAMPLE.guild,
        quests: [{ ...SERVICES_PANEL_SAMPLE.guild.quests[0], state: "failed" }],
      },
    };
    const detail = mountDrawer({ services }).get('[data-testid="lore-drawer__quest-detail--q_1042"]');
    expect(detail.text()).toContain("失敗");
  });

  it("unavailable services: renders only the registry-owned reason, no host/summary/guild blocks", () => {
    const w = mountDrawer({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
    const reason = w.get('[data-testid="lore-drawer__unavailable"]');
    expect(reason.text()).toBe("服務選單目前無法顯示");
    expect(w.find('[data-testid="lore-drawer__host"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__summary"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__guild"]').exists()).toBe(false);
    expect(w.find('[data-testid="lore-drawer__absent"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="lore-drawer__board-lore--"]')).toHaveLength(0);
  });
});
