// redesign-rest-entry design D8: the rest entry's wait form mirrors the sleep
// form element for element — 等待直到黎明, a bounded hours input that
// converts once to whole seconds, SleepForm's Chinese validation, the locked
// state, and Escape handing control back to the shell.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import WaitForm from "../../components/WaitForm.vue";

const BOUND_ERROR = "請輸入有效時長，最短 1 秒、最長 12 小時。";

describe("WaitForm (redesign-rest-entry)", () => {
  let wrapper;

  function mountForm(props = {}) {
    wrapper = mount(WaitForm, { props, attachTo: document.body });
    return wrapper;
  }

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the dawn button, the hours input, the hint, and the submit button", () => {
    mountForm();
    expect(wrapper.attributes("data-testid")).toBe("wait-form");
    const dawn = wrapper.get('[data-testid="wait-form-dawn"]');
    expect(dawn.text()).toBe("等待直到黎明");
    // The dawn button is the form's first control.
    expect(wrapper.element.querySelector("button, input")).toBe(dawn.element);
    const input = wrapper.get('input[type="number"]');
    expect(input.attributes("aria-label")).toBe("等待時長（小時）");
    expect(input.element.value).toBe("1");
    expect(wrapper.text()).toContain("或指定時長（小時）");
    expect(wrapper.get("small").text()).toBe("最長 12 小時，可輸入小數。");
    expect(wrapper.get('button[type="submit"]').text()).toBe("等待此時長");
    // Autofocus lands on the duration input.
    expect(document.activeElement).toBe(input.element);
  });

  it("emits dawn once when 等待直到黎明 is clicked", async () => {
    mountForm();
    await wrapper.get('[data-testid="wait-form-dawn"]').trigger("click");
    expect(wrapper.emitted("dawn")).toHaveLength(1);
    expect(wrapper.emitted("submit")).toBeUndefined();
  });

  it("converts 0.25 hours once to 900 seconds", async () => {
    mountForm();
    await wrapper.get("input").setValue("0.25");
    await wrapper.trigger("submit");
    expect(wrapper.emitted("submit")).toEqual([[900]]);
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
  });

  it("rejects an empty, zero, or over-bound value with the Chinese error and no submit", async () => {
    mountForm();
    for (const value of ["", "0", "13"]) {
      await wrapper.get("input").setValue(value);
      await wrapper.trigger("submit");
      expect(wrapper.get('[role="alert"]').text()).toBe(BOUND_ERROR);
      expect(wrapper.get("input").attributes("disabled")).toBeUndefined();
    }
    expect(wrapper.emitted("submit")).toBeUndefined();
    expect(wrapper.emitted("error")).toHaveLength(3);
  });

  it("emits nothing while disabled", async () => {
    mountForm({ disabled: true });
    expect(wrapper.get('[data-testid="wait-form-dawn"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('button[type="submit"]').attributes("disabled")).toBeDefined();
    // A direct click on the disabled control and a submit (Enter in the
    // input) are both ignored.
    await wrapper.get('[data-testid="wait-form-dawn"]').trigger("click");
    await wrapper.trigger("submit");
    expect(wrapper.emitted("dawn")).toBeUndefined();
    expect(wrapper.emitted("submit")).toBeUndefined();
  });

  it("emits close on Escape in the input and keeps the key from bubbling", async () => {
    mountForm();
    const outer = [];
    document.body.addEventListener("keydown", (event) => outer.push(event.key));
    await wrapper.get("input").trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(outer).toEqual([]);
  });
});
