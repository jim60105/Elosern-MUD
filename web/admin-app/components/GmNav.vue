<script setup>
// The GM side navigation (gm-portal-s1-foundation): brand, ornament rule,
// and one entry per sub-project. Delivered sections are links that emit
// `navigate`; undelivered ones are inert, unfocusable spans marked
// aria-disabled with the 「尚未開放」 tag — no href, no handler, no
// placeholder page behind them.
import { DISABLED_SECTION_TAG } from "../lib/sections.js";

const props = defineProps({
  items: { type: Array, required: true },
  activeKey: { type: String, default: "" },
  homeHref: { type: String, default: "/gm/" },
});

const emit = defineEmits(["navigate"]);

function ordinal(index) {
  return String(index + 1).padStart(2, "0");
}

function follow(event, item) {
  // Leave modified clicks (new tab/window) to the browser.
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }
  event.preventDefault();
  emit("navigate", item);
}

const home = () => props.items.find((item) => item.href) ?? null;
</script>

<template>
  <div class="gm-nav">
    <a
      class="gm-nav__brand"
      :href="homeHref"
      aria-label="Elosern GM 控制台，回到總覽"
      @click="home() && follow($event, home())"
    >
      <span class="gm-nav__wordmark">ELOSERN</span>
      <span class="gm-nav__product">GM 控制台</span>
    </a>
    <span class="gm-nav__rule" aria-hidden="true"></span>
    <nav aria-label="GM 主選單">
      <ul class="gm-nav__list">
        <li v-for="(item, index) in items" :key="item.key">
          <a
            v-if="item.href"
            class="gm-nav__item"
            :class="{ 'is-active': item.key === activeKey }"
            :href="item.href"
            :aria-current="item.key === activeKey ? 'page' : null"
            :data-section="item.key"
            @click="follow($event, item)"
          >
            <span class="gm-nav__ordinal" aria-hidden="true">{{ ordinal(index) }}</span>
            <span class="gm-nav__label">{{ item.label }}</span>
          </a>
          <span
            v-else
            class="gm-nav__item gm-nav__item--disabled"
            aria-disabled="true"
            :data-section="item.key"
          >
            <span class="gm-nav__ordinal" aria-hidden="true">{{ ordinal(index) }}</span>
            <span class="gm-nav__label">{{ item.label }}<span class="gm-visually-hidden">，</span></span>
            <span class="gm-nav__tag">{{ DISABLED_SECTION_TAG }}</span>
          </span>
        </li>
      </ul>
    </nav>
  </div>
</template>

<style scoped>
.gm-nav {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.gm-nav__brand {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  height: 72px;
  padding: 0 var(--sp-5);
  text-decoration: none;
  border-radius: var(--radius-sm);
}

.gm-nav__wordmark {
  font-family: var(--f-display);
  font-size: var(--text-lg);
  line-height: 1.1;
  letter-spacing: 0.24em;
  color: var(--gold-400);
}

.gm-nav__product {
  font-size: var(--text-xs);
  letter-spacing: 0.16em;
  color: var(--paper-500);
}

.gm-nav__rule {
  display: block;
  height: 11px;
  margin: var(--sp-2) var(--sp-5) var(--sp-3);
  background:
    var(--band-ornament) center / 30px 11px no-repeat,
    linear-gradient(90deg, transparent, var(--band-edge-dim) 20%, var(--band-edge-dim) 80%, transparent)
      center / 100% 1px no-repeat;
}

.gm-nav__list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-3);
  list-style: none;
}

.gm-nav__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  min-height: 44px;
  padding: 0 var(--sp-3);
  font-size: var(--text-md);
  font-weight: 500;
  color: var(--paper-300);
  text-decoration: none;
  border-radius: var(--radius-sm);
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}

.gm-nav__label {
  white-space: nowrap;
}

.gm-nav__ordinal {
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--paper-500);
}

a.gm-nav__item:hover {
  color: var(--paper-50);
  background: var(--ink-820);
}

a.gm-nav__item:active {
  background: var(--ink-780);
}

.gm-nav__item.is-active {
  font-weight: 600;
  color: var(--gold-300);
  background: linear-gradient(90deg, var(--gold-glow), transparent 85%);
}

.gm-nav__item.is-active::before {
  content: "";
  position: absolute;
  top: 8px;
  bottom: 8px;
  left: 0;
  width: 3px;
  background: var(--gold-500);
  border-radius: 2px;
}

.gm-nav__item.is-active .gm-nav__ordinal {
  color: var(--gold-500);
}

.gm-nav__item--disabled {
  color: var(--paper-500);
  cursor: default;
}

.gm-nav__item--disabled .gm-nav__ordinal {
  color: var(--paper-700);
}

.gm-nav__tag {
  margin-left: auto;
  padding: 0 var(--sp-2);
  font-size: var(--text-xs);
  font-weight: 400;
  line-height: 1.6;
  color: var(--paper-500);
  white-space: nowrap;
  border: 1px dashed var(--ink-600);
  border-radius: var(--radius-pill);
}

@media (max-width: 859px) {
  .gm-nav__brand {
    height: 56px;
  }

  .gm-nav__rule,
  .gm-nav__ordinal {
    display: none;
  }

  .gm-nav__list {
    flex-direction: row;
    overflow-x: auto;
    scroll-snap-type: x proximity;
    padding-bottom: var(--sp-3);
  }

  .gm-nav__list > li {
    flex: none;
    scroll-snap-align: start;
  }

  .gm-nav__item {
    min-height: 40px;
  }

  .gm-nav__item.is-active::before {
    top: auto;
    right: 8px;
    bottom: 0;
    left: 8px;
    width: auto;
    height: 3px;
  }
}
</style>
