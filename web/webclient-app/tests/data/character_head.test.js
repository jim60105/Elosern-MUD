import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import CharacterHead from "../../components/CharacterHead.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

// H2 (webclient-hud-02-status-islands), design D2/D11: the head card renders
// only backed identity — a glyph portrait (never an image), the numeric
// magic_level badge, the display name, the derived rank title paired with
// guild rank/merit, the wallet, and the disguise marker. No race,
// subrace, class, or faction line (no such field exists in either payload),
// and the wallet is the HUD's single persistent surface.

describe("CharacterHead (H2 head-card island)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountHead(props = {}) {
    wrapper = mount(CharacterHead, {
      props: {
        status: STATUS_PANEL_SAMPLE,
        character: CHARACTER_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the glyph portrait, the magic badge, the name, the rank line, the wallet, and the disguise marker", () => {
    const w = mountHead();
    expect(w.get('[data-testid="character-head__glyph"]').text()).toBe("艾");
    expect(w.get('[data-testid="character-head__badge"]').text()).toBe("31");
    expect(w.get('[data-testid="character-head__name"]').text()).toBe("艾倫·灰誓");
    const rank = w.get('[data-testid="character-head__rank"]').text();
    expect(rank).toContain("魔階·大師");
    expect(rank).toContain("公會 E");
    expect(rank).toContain("功績 140");
    expect(w.get('[data-testid="character-head__wallet"]').text()).toBe("錢包 3,240 銅");
    expect(w.get('[data-testid="character-head__disguise"]').text()).toBe("目前有偽裝");
  });

  it("renders a glyph portrait tile, never an image element", () => {
    const w = mountHead();
    expect(w.find('img').exists()).toBe(false);
    expect(w.get('[data-testid="character-head__portrait"]').exists()).toBe(true);
  });

  it("renders no race, subrace, class, or faction line", () => {
    const w = mountHead();
    const text = w.text();
    for (const word of ["種族", "亞種", "職業", "派系", "同盟"]) {
      expect(text).not.toContain(word);
    }
  });

  it("keeps the true magic_level on the badge and rank line under an active disguise", () => {
    // The fixture's disguise carries a displayed magic_level of 12, but the
    // true trait is 31 — the card must keep the true value (design D2).
    const w = mountHead();
    expect(w.get('[data-testid="character-head__badge"]').text()).toBe("31");
    expect(
      w.get('[data-testid="character-head__rank"]').text(),
    ).toContain("魔階·大師");
  });

  it("omits the guild line when the payload has no guild object", () => {
    const w = mountHead({ character: { ...CHARACTER_PANEL_SAMPLE, guild: null } });
    const rank = w.get('[data-testid="character-head__rank"]').text();
    expect(rank).toContain("魔階·大師");
    expect(rank).not.toContain("公會");
  });

  it("renders 未加入公會 for a null guild rank", () => {
    const w = mountHead({
      character: { ...CHARACTER_PANEL_SAMPLE, guild: { rank: null, merit: 0 } },
    });
    expect(
      w.get('[data-testid="character-head__rank"]').text(),
    ).toContain("未加入公會");
  });

  it("renders an empty portrait tile for an empty display name", () => {
    const w = mountHead({
      status: {
        ...STATUS_PANEL_SAMPLE,
        actor: { ...STATUS_PANEL_SAMPLE.actor, name: "" },
      },
    });
    expect(w.get('[data-testid="character-head__glyph"]').text()).toBe("");
  });
});
