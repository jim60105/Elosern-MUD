<script setup>
// CreationConceptGuide (creation-stepped-form; design §8): the concept page's
// guide column. It suggests what to write, lists what a concept apply fills,
// and marks each item once the current proposal actually carries a value for
// it. It reads the proposal and never changes it; sex and portrait are never
// generated, so they are never listed as filled.
import { computed } from "vue";

const props = defineProps({
  // The committed panel's transient proposal slot, or null.
  proposal: { type: Object, default: null },
});

const QUESTIONS = Object.freeze([
  "出身哪裡、在什麼環境長大？",
  "靠什麼維生、擅長什麼？",
  "性格如何、有什麼習慣？",
  "為什麼踏上旅途？",
]);

// Each listed item and the proposal keys that fill it.
const FILLS = Object.freeze([
  { label: "名稱", keys: ["display_name"] },
  { label: "年齡與外觀年齡", keys: ["age", "apparent_age"] },
  { label: "種族與血統", keys: ["race", "subrace"] },
  { label: "能力配點", keys: ["allocations"] },
  { label: "元素親和", keys: ["affinity_elements"] },
  { label: "背景", keys: ["background"] },
  { label: "個性", keys: ["persona.personality"] },
  { label: "生平", keys: ["persona.life_story"] },
  { label: "習慣", keys: ["persona.habit"] },
]);

function valueAt(source, path) {
  return path.split(".").reduce((node, key) => (node && typeof node === "object" ? node[key] : undefined), source);
}

// A value is present when the apply has something to write: a non-empty
// string, any finite number (zero included), a non-empty list, or an object
// carrying at least one finite number (the allocation axes).
function present(value) {
  if (typeof value === "string") return value !== "";
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.length > 0;
  if (value && typeof value === "object") {
    return Object.values(value).some((member) => typeof member === "number" && Number.isFinite(member));
  }
  return false;
}

const items = computed(() => FILLS.map((fill) => ({
  ...fill,
  filled: !!props.proposal && fill.keys.some((key) => present(valueAt(props.proposal, key))),
})));
</script>

<template>
  <aside class="creation-guide" data-testid="creation-concept-guide">
    <section class="creation-guide__block">
      <h3 class="creation-guide__title">可以寫些什麼</h3>
      <ol class="creation-guide__asks">
        <li v-for="question in QUESTIONS" :key="question">{{ question }}</li>
      </ol>
    </section>
    <section class="creation-guide__block">
      <h3 class="creation-guide__title">會幫你填好</h3>
      <ul class="creation-guide__fills">
        <li
          v-for="item in items"
          :key="item.label"
          data-testid="creation-concept-fill"
          :data-fill-keys="item.keys.join(' ')"
          :data-present="item.filled ? 'true' : 'false'"
        >
          <i aria-hidden="true"></i>{{ item.label }}<span class="creation-guide__sr">{{ item.filled ? "（已填入）" : "（未填入）" }}</span>
        </li>
      </ul>
    </section>
    <p class="creation-guide__note">性別與肖像不會自動產生，套用後請在自由創建中補上。</p>
  </aside>
</template>

<style scoped src="./creation-concept-guide.css"></style>
