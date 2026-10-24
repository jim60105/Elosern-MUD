import { h } from "vue";
import WaitForm from "../../components/WaitForm.vue";

// WaitForm (redesign-rest-entry design D8): the rest entry's second-layer
// wait form, the wait-side mirror of SleepForm. Deterministic offline args:
// the browser collects 等待直到黎明 or a bounded hours value; the server
// validates the `explore.wait` request and advances the clock.

const renderForm = (args) => ({
  render: () => h("div", { style: "max-width: 320px;" }, [h(WaitForm, args)]),
});

export default {
  title: "Action/WaitForm",
  component: WaitForm,
  parameters: {
    docs: {
      description: {
        component:
          "The wait form offers 等待直到黎明 (emits `dawn`) or a bounded duration " +
          "in hours that converts once to whole seconds (emits `submit(seconds)`). " +
          "Escape emits `close`; the shell steps back. Locked, every control is disabled.",
      },
    },
  },
  argTypes: {
    onDawn: { action: "dawn" },
    onSubmit: { action: "submit" },
    onClose: { action: "close" },
  },
};

export const Default = {
  render: renderForm,
  args: {},
};

export const Locked = {
  render: renderForm,
  args: { disabled: true },
};
