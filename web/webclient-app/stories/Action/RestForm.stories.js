import { h } from "vue";
import RestForm from "../../components/RestForm.vue";

// RestForm (C4, webclient-vue-10-wire-views-browser): the keyboard-operable
// bounded rest-duration form. Deterministic offline args: the `max` cap
// values — the browser collects the value; the server parses and validates
// it (the browser never advances its own clock).

const renderForm = (args) => ({
  render: () =>
    h("div", { style: "max-width: 320px;" }, [h(RestForm, args)]),
});

export default {
  title: "Action/RestForm",
  component: RestForm,
  parameters: {
    docs: {
      description: {
        component:
          "The bounded duration form collects hours using a native numeric " +
          "input and converts them to bounded integer seconds. The server " +
          "validates and advances the clock. Slash while " +
          "open never toggles the command drawer.",
      },
    },
  },
};

export const DefaultCap = {
  render: renderForm,
  args: { max: 43200 },
};

export const SmallCap = {
  render: renderForm,
  args: { max: 3600 },
};
