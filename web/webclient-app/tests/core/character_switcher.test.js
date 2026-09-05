import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import CharacterSwitcher from "../../components/CharacterSwitcher.vue";

describe("CharacterSwitcher (MC5, multichar-05-topbar-switcher-ui)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  const SAMPLE_CHARACTERS = [
    {
      identity: 1,
      name: "艾莉亞",
      current: true,
      pending: false,
      portrait: {
        subject_key: "char_1",
        status: "done",
        url: "/art/portraits/char_1.webp",
        aspect_ratio: "3/4",
        alt: "艾莉亞的肖像",
        placeholder: null,
      },
    },
    {
      identity: 2,
      name: "雷恩",
      current: false,
      pending: false,
      portrait: {
        subject_key: "char_2",
        status: "pending",
        url: null,
        aspect_ratio: "3/4",
        alt: "雷恩的肖像",
        placeholder: { kind: "generating", label: "肖像生成中" },
      },
    },
    {
      identity: 3,
      name: "新冒險者",
      current: false,
      pending: true,
      portrait: {
        subject_key: null,
        status: "missing",
        url: null,
        aspect_ratio: "3/4",
        alt: "新冒險者的肖像",
        placeholder: { kind: "silhouette", label: "未建立" },
      },
    },
  ];

  it("renders nothing when the roster is unavailable, empty, or has no current character", () => {
    wrapper = mount(CharacterSwitcher, {
      props: { available: false, characters: SAMPLE_CHARACTERS },
    });
    expect(wrapper.find('[data-testid="character-switcher"]').exists()).toBe(false);

    wrapper.unmount();
    wrapper = mount(CharacterSwitcher, {
      props: { available: true, characters: [] },
    });
    expect(wrapper.find('[data-testid="character-switcher"]').exists()).toBe(false);

    wrapper.unmount();
    const noCurrent = SAMPLE_CHARACTERS.map((c) => ({ ...c, current: false }));
    wrapper = mount(CharacterSwitcher, {
      props: { available: true, characters: noCurrent },
    });
    expect(wrapper.find('[data-testid="character-switcher"]').exists()).toBe(false);
  });

  it("collapsed pill reads the current row's name and portrait thumbnail", () => {
    wrapper = mount(CharacterSwitcher, {
      props: { available: true, characters: SAMPLE_CHARACTERS },
    });
    const trigger = wrapper.get('[data-testid="character-switcher-trigger"]');
    expect(trigger.attributes("aria-expanded")).toBe("false");
    expect(trigger.attributes("aria-haspopup")).toBe("dialog");
    expect(wrapper.get('[data-testid="character-switcher-name"]').text()).toBe("艾莉亞");
    const img = wrapper.get(".character-switcher__thumb");
    expect(img.attributes("src")).toBe("/art/portraits/char_1.webp");
    expect(img.attributes("alt")).toBe("艾莉亞的肖像");
  });

  it("collapsed pill uses placeholder when current character has no url", () => {
    const chars = [
      {
        identity: 2,
        name: "雷恩",
        current: true,
        pending: false,
        portrait: {
          subject_key: "char_2",
          status: "pending",
          url: null,
          aspect_ratio: "3/4",
          alt: "雷恩的肖像",
          placeholder: { kind: "generating", label: "生成中" },
        },
      },
    ];
    wrapper = mount(CharacterSwitcher, {
      props: { available: true, characters: chars },
    });
    expect(wrapper.get('[data-testid="character-switcher-name"]').text()).toBe("雷恩");
    expect(wrapper.get('[data-testid="character-switcher-placeholder"]').text()).toBe("生成中");
  });

  it("expanded popover lists roster rows in payload order with the current one selected and non-activatable", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: { available: true, characters: SAMPLE_CHARACTERS, canCreate: true },
    });
    // Click to expand
    await wrapper.get('[data-testid="character-switcher-trigger"]').trigger("click");
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(true);

    const rows = wrapper.findAll(".character-switcher__row");
    expect(rows).toHaveLength(3);

    // Row 1: current
    expect(rows[0].text()).toContain("艾莉亞");
    expect(rows[0].classes()).toContain("is-current");
    expect(rows[0].attributes("disabled")).toBeDefined();
    expect(rows[0].attributes("aria-current")).toBe("true");

    // Row 2: non-current, enabled
    expect(rows[1].text()).toContain("雷恩");
    expect(rows[1].classes()).not.toContain("is-current");
    expect(rows[1].attributes("disabled")).toBeUndefined();

    // Row 3: pending creation sibling
    expect(rows[2].text()).toContain("新冒險者");
    expect(rows[2].classes()).toContain("is-pending");
    const badge = rows[2].find('[data-testid="character-pending-badge"]');
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe("建立中");
  });

  it("shared lock note renders when switchLocked with reason, and disables all non-current rows", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        switchLocked: true,
        lockReason: "戰鬥中無法切換角色",
        canCreate: true,
        initialExpanded: true,
      },
    });

    const lockNotes = wrapper.findAll('[data-testid="character-switcher-lock-note"]');
    expect(lockNotes).toHaveLength(1);
    expect(lockNotes[0].text()).toBe("戰鬥中無法切換角色");

    // All rows are disabled
    const rows = wrapper.findAll(".character-switcher__row");
    for (const row of rows) {
      expect(row.attributes("disabled")).toBeDefined();
    }
    // No per-row lock badge
    expect(wrapper.findAll(".character-switcher__row-lock-badge")).toHaveLength(0);
  });

  it("clicking an enabled non-current row dispatches switch-character once with identity and does not close popover", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        canCreate: true,
        initialExpanded: true,
      },
    });

    const row2 = wrapper.get('[data-testid="character-row-2"]');
    await row2.trigger("click");

    expect(wrapper.emitted("switch-character")).toEqual([[2]]);
    // Must NOT close on dispatch alone (D7)
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(true);
    // Selection does NOT optimistically move
    expect(wrapper.get('[data-testid="character-switcher-name"]').text()).toBe("艾莉亞");
  });

  it("updating characters prop without changing epoch does not close the popover", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        epoch: 1,
        initialExpanded: true,
      },
    });

    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(true);

    // Update characters prop
    const updatedChars = [...SAMPLE_CHARACTERS, {
      identity: 4,
      name: "第四名角色",
      current: false,
      pending: false,
      portrait: null,
    }];
    await wrapper.setProps({ characters: updatedChars });
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(true);
  });

  it("changing epoch prop closes the popover and resets confirmation", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        epoch: 1,
        canCreate: true,
        initialExpanded: true,
      },
    });

    // Enter confirmation
    await wrapper.get('[data-testid="character-create-control"]').trigger("click");
    expect(wrapper.find('[data-testid="character-create-confirm-panel"]').exists()).toBe(true);

    // Epoch changes (server snapshot committed)
    await wrapper.setProps({ epoch: 2 });
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(false);
  });

  it("create control is confirmation-gated: opens confirmation without dispatching, confirm dispatches once", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        canCreate: true,
        initialExpanded: true,
      },
    });

    const createBtn = wrapper.get('[data-testid="character-create-control"]');
    expect(createBtn.attributes("disabled")).toBeUndefined();
    expect(createBtn.text()).toContain("＋ 新增角色");

    // Click to enter confirmation
    await createBtn.trigger("click");
    expect(wrapper.emitted("create-character")).toBeUndefined();
    expect(wrapper.find('[data-testid="character-create-confirm-panel"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="character-create-confirm-message"]').text()).toContain(
      "即將離開當前角色並進入角色建立流程。",
    );

    // Cancel exits confirmation back to roster list
    await wrapper.get('[data-testid="character-create-cancel"]').trigger("click");
    expect(wrapper.emitted("create-character")).toBeUndefined();
    expect(wrapper.find('[data-testid="character-create-confirm-panel"]').exists()).toBe(false);
    expect(wrapper.findAll(".character-switcher__row")).toHaveLength(3);

    // Re-enter confirmation and confirm
    await wrapper.get('[data-testid="character-create-control"]').trigger("click");
    await wrapper.get('[data-testid="character-create-confirm"]').trigger("click");
    expect(wrapper.emitted("create-character")).toHaveLength(1);
    // Does NOT close on dispatch alone
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(true);
  });

  it("capacity-disabled create control displays reason and cannot open confirmation", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        canCreate: false,
        initialExpanded: true,
      },
    });

    const createBtn = wrapper.get('[data-testid="character-create-control"]');
    expect(createBtn.attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-testid="character-switcher-capacity-reason"]').text()).toBe(
      "角色數量已達上限",
    );

    await createBtn.trigger("click");
    expect(wrapper.find('[data-testid="character-create-confirm-panel"]').exists()).toBe(false);
    expect(wrapper.emitted("create-character")).toBeUndefined();
  });

  it("confirmation submit button disables and refuses dispatch if canCreate becomes false while confirming", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        canCreate: true,
        initialExpanded: true,
      },
    });

    // Enter confirmation
    await wrapper.get('[data-testid="character-create-control"]').trigger("click");
    const confirmBtn = wrapper.get('[data-testid="character-create-confirm"]');
    expect(confirmBtn.attributes("disabled")).toBeUndefined();

    // Capacity becomes full before submit
    await wrapper.setProps({ canCreate: false });
    expect(confirmBtn.attributes("disabled")).toBeDefined();

    await confirmBtn.trigger("click");
    expect(wrapper.emitted("create-character")).toBeUndefined();
  });

  it("locking does not dismiss an open popover but disables inner buttons", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        canCreate: true,
        locked: false,
        initialExpanded: true,
      },
    });

    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(true);

    // Locked transition (e.g. transport lost)
    await wrapper.setProps({ locked: true });
    // Must NOT dismiss the popover (contract: closes only on Escape, outside pointerdown, or epoch commit)
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(true);

    // All buttons inside must now be disabled
    for (const row of wrapper.findAll(".character-switcher__row")) {
      expect(row.attributes("disabled")).toBeDefined();
    }
    expect(
      wrapper.get('[data-testid="character-create-control"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("focus management: confirmation open moves focus to confirm button, Escape restores focus to trigger", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        canCreate: true,
        initialExpanded: true,
      },
      attachTo: document.body,
    });

    const trigger = wrapper.get('[data-testid="character-switcher-trigger"]').element;
    await wrapper.get('[data-testid="character-create-control"]').trigger("click");
    await wrapper.vm.$nextTick();

    const confirmBtn = wrapper.get('[data-testid="character-create-confirm"]').element;
    expect(document.activeElement).toBe(confirmBtn);

    // First Escape: exits confirmation back to list
    await wrapper.get('[data-testid="character-switcher"]').trigger("keydown", { key: "Escape" });
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="character-create-confirm-panel"]').exists()).toBe(false);

    // Second Escape: closes popover and restores focus to trigger
    await wrapper.get('[data-testid="character-switcher"]').trigger("keydown", { key: "Escape" });
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(false);
    expect(document.activeElement).toBe(trigger);
  });

  it("locked or disconnected state disables all controls", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        canCreate: true,
        locked: true,
      },
    });

    const trigger = wrapper.get('[data-testid="character-switcher-trigger"]');
    expect(trigger.attributes("disabled")).toBeDefined();

    // Clicking trigger does not open when locked
    await trigger.trigger("click");
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(false);

    // If mounted initially expanded with locked=true
    wrapper.unmount();
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        canCreate: true,
        locked: true,
        initialExpanded: true,
      },
    });
    for (const row of wrapper.findAll(".character-switcher__row")) {
      expect(row.attributes("disabled")).toBeDefined();
    }
    expect(
      wrapper.get('[data-testid="character-create-control"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("Escape key closes confirmation first, then closes popover on second escape", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        canCreate: true,
        initialExpanded: true,
      },
      attachTo: document.body,
    });

    // Enter confirmation
    await wrapper.get('[data-testid="character-create-control"]').trigger("click");
    expect(wrapper.find('[data-testid="character-create-confirm-panel"]').exists()).toBe(true);

    // First Escape: exits confirmation
    await wrapper.get('[data-testid="character-switcher"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.find('[data-testid="character-create-confirm-panel"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(true);
    expect(wrapper.emitted("create-character")).toBeUndefined();

    // Second Escape: closes popover
    await wrapper.get('[data-testid="character-switcher"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(false);
  });

  it("outside pointerdown closes popover", async () => {
    wrapper = mount(CharacterSwitcher, {
      props: {
        available: true,
        characters: SAMPLE_CHARACTERS,
        initialExpanded: true,
      },
      attachTo: document.body,
    });

    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(true);

    // Outside pointerdown
    const outsideEl = document.createElement("div");
    document.body.appendChild(outsideEl);
    const event = new MouseEvent("pointerdown", { bubbles: true });
    outsideEl.dispatchEvent(event);
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="character-switcher-popover"]').exists()).toBe(false);
    outsideEl.remove();
  });
});
