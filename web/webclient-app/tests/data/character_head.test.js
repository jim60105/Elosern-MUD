import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import CharacterHead from "../../components/CharacterHead.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  STATUS_PANEL_SAMPLE,
  STATUS_PANEL_TITLED_SAMPLE,
} from "../../stories/fixtures.js";

// H2 (webclient-hud-02-status-islands), design D2/D11: the head card renders
// only backed identity — a glyph portrait (never an image), the numeric
// magic_power badge, the display name, the guild rank/merit line, the wallet,
// and the disguise marker. No magic-derived rank word appears in any form
// (magic-power-static-rename), and no race, subrace, class, or faction line
// exists in either payload. The wallet is the HUD's single persistent surface.

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
    expect(rank).toContain("公會 E");
    expect(rank).toContain("功績 140");
    expect(rank).not.toMatch(/學徒|術師|大師|賢者|主宰/);
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

  it("keeps the true magic_power on the badge under an active disguise", () => {
    // The fixture's disguise carries a displayed magic_power of 12, but the
    // true trait is 31 — the badge must keep the true value (design D2).
    const w = mountHead();
    expect(w.get('[data-testid="character-head__badge"]').text()).toBe("31");
    expect(
      w.get('[data-testid="character-head__rank"]').text(),
    ).toContain("公會 E");
  });

  it("shows the explicit marker when the payload has no guild object", () => {
    const w = mountHead({ character: { ...CHARACTER_PANEL_SAMPLE, guild: null } });
    const rank = w.get('[data-testid="character-head__rank"]').text();
    expect(rank).toContain("未加入公會");
    expect(rank).toContain("功績 0");
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

  // title-system D6: the head card addresses the player by the composed full
  // title when the committed status panel carries one, and falls back to the
  // plain name when the row is absent or empty (never a blank heading).
  it("addresses the player by the composed full title when the panel carries one", () => {
    const w = mountHead({ status: STATUS_PANEL_TITLED_SAMPLE });
    expect(w.get('[data-testid="character-head__name"]').text()).toBe(
      "F級冒險者　南門新客",
    );
    // The glyph stays the character's own name, never the title's first char.
    expect(w.get('[data-testid="character-head__glyph"]').text()).toBe("艾");
  });

  it("renders a fixed-only title and keeps the rank line independent", () => {
    const fixedOnly = {
      ...STATUS_PANEL_TITLED_SAMPLE,
      actor: { ...STATUS_PANEL_TITLED_SAMPLE.actor, full_title: "S級傳說" },
    };
    const w = mountHead({ status: fixedOnly });
    expect(w.get('[data-testid="character-head__name"]').text()).toBe("S級傳說");
  });

  it("falls back to the plain name when full_title is absent or empty", () => {
    const empty = {
      ...STATUS_PANEL_SAMPLE,
      actor: { ...STATUS_PANEL_SAMPLE.actor, full_title: "" },
    };
    expect(mountHead({ status: empty }).get('[data-testid="character-head__name"]').text()).toBe(
      "艾倫·灰誓",
    );
    expect(
      mountHead({ status: STATUS_PANEL_SAMPLE }).get('[data-testid="character-head__name"]').text(),
    ).toBe("艾倫·灰誓");
  });
});
