<script setup>
// The approved creation layout (reference only, synthetic data, not imported
// by the app): a card wall for the presets, a stepped custom form beside a
// persistent portrait slot, and a guided concept page. The figures are the
// committed built-in defaults, so the stories render on any checkout.
import { computed, ref } from "vue";
import GalleryGenerateDrawer from "../../../web/webclient-app/components/GalleryGenerateDrawer.vue";
import { AXES, DRAFT_GALLERY_MODEL, ELEMENTS, PRESETS, SILHOUETTES } from "./prototype-data.js";

const props = defineProps({
  mode: { type: String, default: "preset" },
  selected: { type: Number, default: 2 },
  // The custom portrait slot: empty (silhouette), pending, ready.
  portrait: { type: String, default: "empty" },
  drawer: { type: Boolean, default: false },
  step: { type: Number, default: 0 },
});

const tab = ref(props.mode);
const index = ref(props.selected);
const sex = ref("female");
const drawerOpen = ref(props.drawer);
const step = ref(props.step);
const current = computed(() => PRESETS[index.value]);
const count = PRESETS.length;
const move = (offset) => { index.value = (index.value + offset + count) % count; };
const silhouette = computed(() => SILHOUETTES[sex.value]);
const pad = (n) => String(n).padStart(2, "0");
const STEPS = ["身分", "角色故事", "能力配置"];
const ASKS = ["出身哪裡、在什麼環境長大？", "靠什麼維生、擅長什麼？", "性格如何、有什麼習慣？", "為什麼踏上旅途？"];
const FILLS = ["名稱", "年齡與外觀年齡", "種族與血統", "能力配點", "元素親和", "背景", "個性", "生平", "習慣"];
const conceptDone = props.portrait === "ready";
const TABS = [["preset", "預設角色"], ["custom", "自由創建"], ["concept", "概念生成"]];
</script>

<template>
  <section class="cp" :data-mode="tab">
    <header class="cp-head">
      <div class="cp-brand">
        <p class="cp-eyebrow">ELOSERN ‧ 伊洛瑟恩</p>
        <h2 class="cp-title">角色創建</h2>
      </div>
      <nav class="ui-tabs cp-tabs" aria-label="建角方式">
        <button v-for="[key, label] in TABS" :key="key" type="button" class="ui-tabs__tab"
          :class="{ 'is-active': tab === key }" :aria-pressed="tab === key" @click="tab = key">{{ label }}</button>
      </nav>
      <p class="cp-intro">選擇起點，寫下你的故事。</p>
    </header>

    <!-- ───────────── PRESET ───────────── -->
    <div v-if="tab === 'preset'" class="cp-body cp-preset">
        <div class="wall">
          <article v-for="(card, i) in PRESETS" :key="card.key" class="wall-card" :data-open="i === index" @click="index = i">
            <div class="wall-art" :style="{ backgroundImage: `url(${card.art})` }"></div>
            <button v-if="i !== index" type="button" class="wall-spine" :aria-label="card.name">
              <span class="wall-no">{{ pad(i + 1) }}</span>
              <span class="wall-name">{{ card.name }}</span>
            </button>
            <div v-else class="wall-detail">
              <p class="cp-eyebrow">預設角色　{{ pad(i + 1) }} / {{ pad(count) }}</p>
              <h3 class="dossier-name">{{ card.name }}</h3>
              <p class="dossier-race"><span>{{ card.race }}</span><i aria-hidden="true"></i><span>{{ card.subrace }}</span></p>
              <hr class="cp-ornament">
              <p class="dossier-lead">{{ card.emphasis }}</p>
              <p class="dossier-text">{{ card.background }}</p>
              <button type="button" class="ui-btn ui-btn--primary ui-btn--block dossier-cta">以{{ card.name }}啟程</button>
            </div>
          </article>
        </div>
    </div>

    <!-- ───────────── CUSTOM ───────────── -->
    <div v-else-if="tab === 'custom'" class="cp-body cp-custom">
      <!-- The portrait slot shared by every direction. -->
      <aside class="slot" :data-state="portrait">
        <div class="slot-frame">
          <img v-if="portrait === 'ready'" class="slot-art" :src="PRESETS[0].art" alt="角色肖像">
          <span v-else class="slot-shade" :style="{ '--mask': `url(${silhouette})` }" aria-hidden="true"></span>
          <span v-if="portrait === 'pending'" class="slot-pending" role="status"><i aria-hidden="true"></i>肖像繪製中…</span>
          <span class="slot-corner slot-corner--tl" aria-hidden="true"></span><span class="slot-corner slot-corner--br" aria-hidden="true"></span>
        </div>
        <p class="slot-name">{{ portrait === 'ready' ? '林楓' : '尚未命名' }}</p>
        <p class="slot-note">{{ portrait === 'ready' ? '不滿意可以重新繪製。' : portrait === 'pending' ? '可以繼續填寫，完成後會自動出現。' : '填好身分後，為角色繪製肖像。' }}</p>
        <button type="button" class="ui-btn ui-btn--block slot-cta" :disabled="portrait === 'pending'" @click="drawerOpen = true">
          <span aria-hidden="true">✦</span>{{ portrait === 'ready' ? '重新生成肖像' : '生成肖像' }}
        </button>
      </aside>

        <div class="steps">
          <ol class="steps-rail">
            <li v-for="(label, i) in STEPS" :key="label" :data-on="i === step" :data-done="i < step">
              <button type="button" @click="step = i"><span>{{ pad(i + 1) }}</span>{{ label }}<em v-if="i === 2">剩餘 0 點</em></button>
            </li>
          </ol>
          <div class="steps-page">
            <div v-if="step === 0" class="fields fields--two">
              <label class="f f--wide"><span>名稱</span><span class="f-row"><input type="text" value="林楓"><button type="button" class="ui-icon-btn" aria-label="擲名">🎲</button></span></label>
              <label class="f"><span>性別</span><select v-model="sex"><option value="female">女性</option><option value="male">男性</option></select></label>
              <label class="f"><span>種族</span><select><option>人類</option></select></label>
              <label class="f"><span>年齡</span><input type="number" value="21"></label>
              <label class="f"><span>外觀年齡</span><input type="number" value="21"></label>
              <label class="f f--wide"><span>血統</span><select><option>平原人</option></select></label>
              <p class="hint f--wide">人族：均衡、勤奮，長於商貿。遍布大陸各地，是冒險者公會最常見的面孔。</p>
            </div>
            <div v-else-if="step === 1" class="fields fields--two">
              <fieldset class="aff f--wide"><legend>元素親和（上限 2）</legend>
                <label v-for="(el, i) in ELEMENTS" :key="el"><input type="checkbox" :checked="i === 0 || i === 2"><span>{{ el }}</span></label>
              </fieldset>
              <label class="f"><span>背景（可選）</span><textarea rows="4">從渡口學來運貨的年輕人。</textarea></label>
              <label class="f"><span>個性</span><textarea rows="4">沉穩寡言</textarea></label>
              <label class="f"><span>生平</span><textarea rows="4"></textarea></label>
              <label class="f"><span>習慣</span><textarea rows="4"></textarea></label>
            </div>
            <div v-else class="alloc alloc--two">
              <p class="alloc-total f--wide">已配置點數 <b>224</b> / 224</p>
              <div v-for="ax in AXES" :key="ax.key" class="ax">
                <span class="ax-label">{{ ax.label }}</span><span class="ax-help">{{ ax.help }} ‧ {{ ax.min }}–{{ ax.max }}</span>
                <span class="ax-step"><button type="button" class="ui-icon-btn">−</button><input type="number" :value="ax.value"><button type="button" class="ui-icon-btn">+</button></span>
                <span class="ax-bar"><i :style="{ transform: `scaleX(${ax.value / ax.max})` }"></i></span>
              </div>
            </div>
          </div>
          <div class="steps-nav">
            <button type="button" class="ui-btn" :disabled="step === 0" @click="step--">上一步</button>
            <button v-if="step < 2" type="button" class="ui-btn" @click="step++">下一步：{{ STEPS[step + 1] }}</button>
          </div>
        </div>
    </div>

    <div v-else class="cp-body cp-concept">
      <aside class="guide">
        <section>
          <h3 class="guide-title">可以寫些什麼</h3>
          <ol class="guide-ask">
            <li v-for="q in ASKS" :key="q">{{ q }}</li>
          </ol>
        </section>
        <section>
          <h3 class="guide-title">會幫你填好</h3>
          <ul class="guide-fills">
            <li v-for="f in FILLS" :key="f" :data-done="conceptDone"><i aria-hidden="true"></i>{{ f }}</li>
          </ul>
        </section>
        <p class="guide-note">性別與肖像不會自動產生，套用後請在自由創建中補上。</p>
      </aside>
      <section class="concept">
        <h3 class="region-title">從一段描述開始</h3>
        <p class="hint">套用後會帶你到自由創建，每一項都還能修改，確認後才會建立角色。</p>
        <label class="f concept-field"><span>角色概念</span><textarea placeholder="例如：北境礦村出身的年輕獵人，話不多，習慣先觀察再開口。為了找失蹤的兄長離開家鄉……"></textarea></label>
      </section>
    </div>

    <footer class="cp-foot">
      <button type="button" class="ui-btn ui-btn--danger">重設</button>
      <span v-if="tab === 'preset'" class="cp-keys">← → 切換角色　Enter 選擇</span>
      <button v-if="tab === 'custom'" type="button" class="ui-btn ui-btn--primary">確認角色</button>
      <button v-if="tab === 'concept'" type="button" class="ui-btn ui-btn--primary">套用概念</button>
    </footer>

    <GalleryGenerateDrawer v-if="drawerOpen" :model="DRAFT_GALLERY_MODEL" @close="drawerOpen = false" @submit="drawerOpen = false" />
  </section>
</template>

<style scoped>
.cp {
  --u: var(--ui-scale);
  position: absolute; inset: 0; z-index: 40; display: flex; flex-direction: column;
  color: var(--paper-100); font-family: var(--f-sans); color-scheme: dark;
  background:
    radial-gradient(ellipse 60% 70% at 32% 46%, var(--gold-glow), transparent 62%),
    radial-gradient(ellipse at 100% 0%, var(--ink-800), transparent 55%),
    var(--ink-950);
}
.cp[data-mode="custom"], .cp[data-mode="concept"] {
  background: radial-gradient(ellipse 34% 70% at 12% 50%, var(--gold-glow), transparent 70%), var(--ink-950);
}
.cp-head {
  flex: none; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: var(--sp-6);
  padding: var(--sp-3) var(--sp-8); border-bottom: 1px solid var(--band-edge-dim);
  background: linear-gradient(180deg, var(--panel), transparent);
}
.cp-eyebrow { margin: 0; color: var(--paper-500); font-size: var(--text-xs); letter-spacing: 0.18em; }
.cp-title { margin: 0; color: var(--gold-400); font: 400 var(--text-2xl) / 1.4 var(--f-display); letter-spacing: 0.14em; }
.cp-tabs { justify-self: center; align-self: center; }
.cp-tabs .ui-tabs__tab { padding-inline: var(--sp-6); font-size: var(--text-md); }
.cp-intro { margin: 0; justify-self: end; color: var(--paper-500); font: var(--text-md) var(--f-serif); letter-spacing: 0.08em; }
.cp-body { flex: 1; min-height: 0; display: grid; grid-template-rows: minmax(0, 1fr); gap: var(--sp-6); padding: var(--sp-4) var(--sp-8); }
.cp-foot {
  flex: none; display: flex; align-items: center; gap: var(--sp-4);
  padding: var(--sp-3) var(--sp-8); background: var(--ink-900); border-top: 1px solid var(--band-edge);
}
.cp-foot .ui-btn--primary { margin-left: auto; min-width: calc(160px * var(--u)); }
.cp-keys { margin-left: auto; color: var(--paper-500); font-size: var(--text-xs); letter-spacing: 0.08em; }
.cp-ornament { width: 100%; height: calc(11px * var(--u)); margin: 0; border: 0; background: var(--band-ornament) center / contain no-repeat,
  linear-gradient(var(--band-edge-dim), var(--band-edge-dim)) center / 100% 1px no-repeat; }

/* ── preset wall ── */
.cp-preset { grid-template-columns: 1fr; }
.dossier-name { margin: 0; color: var(--gold-300); font: 400 calc(52px * var(--u)) / 1.25 var(--f-display); letter-spacing: 0.1em; }
.dossier-race { display: flex; align-items: center; gap: var(--sp-3); margin: 0; color: var(--paper-300); font: var(--text-md) var(--f-serif); letter-spacing: 0.12em; }
.dossier-race i { width: calc(5px * var(--u)); height: calc(5px * var(--u)); background: var(--gold-500); transform: rotate(45deg); }
.dossier-lead { margin: var(--sp-2) 0 0; color: var(--paper-50); font: var(--text-base) / 1.7 var(--f-serif); }
.dossier-text { margin: 0; color: var(--paper-400); font-size: var(--text-md); line-height: 1.85; }
.dossier-cta { margin-top: var(--sp-3); min-height: calc(48px * var(--u)); font-size: var(--text-md); letter-spacing: 0.12em; }

.wall { min-height: 0; display: flex; gap: var(--sp-2); }
.wall-card {
  position: relative; flex: 1 1 0; min-width: 0; overflow: hidden; cursor: pointer; background: var(--ink-900); container-type: size;
  border: 1px solid var(--band-edge-dim); border-radius: var(--radius-sm);
  transition: flex-grow var(--motion-base, 240ms) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}
.wall-card:hover { border-color: var(--gold-500); }
.wall-card[data-open="true"] { flex-grow: 7; cursor: default; border-color: var(--gold-400); }
/* One size definition for both states: the figure is always card-height tall
   and 9:16 wide (container units), so opening a card only moves and scales
   it. Swapping background-size or the box model here makes the art jump. */
.wall-art {
  position: absolute; top: 0; left: 50%; height: 100cqh; width: 56.25cqh;
  background-size: 100% 100%; background-repeat: no-repeat;
  transform-origin: 50% 0; transform: translateX(-50%) scale(1.18);
  filter: saturate(0.6) brightness(0.62) drop-shadow(0 0 0 transparent);
  transition: left var(--motion-base, 240ms) var(--ease-standard), transform var(--motion-base, 240ms) var(--ease-standard), filter var(--motion-base, 240ms) var(--ease-standard);
}
.wall-card:hover .wall-art { filter: saturate(0.9) brightness(0.9) drop-shadow(0 0 0 transparent); }
.wall-card[data-open="true"] .wall-art { left: 28.125cqh; transform: translateX(-50%) scale(1); filter: saturate(1) brightness(1) drop-shadow(0 0 calc(24px * var(--u)) var(--gold-glow)); }
.wall-spine:focus-visible { outline: 2px solid var(--gold-400); outline-offset: -4px; }
.wall-spine {
  position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: var(--sp-3);
  padding: var(--sp-4) 0; border: 0; color: var(--paper-100); cursor: pointer;
  background: linear-gradient(180deg, transparent 45%, var(--ink-950) 96%);
}
.wall-no { color: var(--gold-500); font: var(--text-xs) var(--f-num); letter-spacing: 0.14em; }
.wall-name { writing-mode: vertical-rl; color: var(--gold-300); font: var(--text-xl) var(--f-display); letter-spacing: 0.18em; }
.wall-detail { position: absolute; inset: 0 0 0 56.25cqh; display: flex; flex-direction: column; gap: var(--sp-2); min-width: 0; padding: var(--sp-5); animation: cp-fade var(--motion-base, 240ms) var(--ease-standard) both; }
@keyframes cp-fade { from { opacity: 0; } }
.wall-detail .dossier-cta { margin-top: auto; }

/* ── custom ── */
.cp-custom { grid-template-columns: calc(340px * var(--u)) minmax(0, 1fr); gap: var(--sp-10, 48px); }
.cp-concept { grid-template-columns: calc(340px * var(--u)) minmax(0, calc(900px * var(--u))); gap: var(--sp-10, 48px); padding-block: var(--sp-6); }
.guide { min-height: 0; overflow-y: auto; scrollbar-width: thin; display: flex; flex-direction: column; gap: var(--sp-5); padding: var(--sp-5); background: var(--panel); border-top: 1px solid var(--band-edge); }
.guide-title { margin: 0 0 var(--sp-2); color: var(--gold-500); font: var(--text-xs) var(--f-sans); letter-spacing: 0.24em; }
.guide-ask { margin: 0; padding-left: 1.4em; color: var(--paper-200); font: var(--text-md) / 1.9 var(--f-serif); }
.guide-ask li::marker { color: var(--gold-500); font-family: var(--f-num); }
.guide-fills { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: auto auto; justify-content: start; white-space: nowrap; gap: var(--sp-1) var(--sp-4); color: var(--paper-300); font-size: var(--text-md); }
.guide-fills li { display: flex; align-items: center; gap: var(--sp-2); }
.guide-fills i { flex: none; width: calc(8px * var(--u)); height: calc(8px * var(--u)); border: 1px solid var(--gold-600); transform: rotate(45deg); }
.guide-fills li[data-done="true"] { color: var(--paper-50); }
.guide-fills li[data-done="true"] i { background: var(--gold-400); border-color: var(--gold-400); }
.guide-note { margin: auto 0 0; padding-top: var(--sp-3); border-top: 1px solid var(--band-edge-dim); color: var(--paper-500); font-size: var(--text-xs); line-height: 1.7; }
.concept { min-height: 0; display: flex; flex-direction: column; gap: var(--sp-3); }
.concept-field { flex: 1; min-height: 0; }
.concept-field textarea { flex: 1; resize: none; line-height: 1.8; }
.concept-field textarea::placeholder { color: var(--paper-700); }
.slot { min-height: 0; display: flex; flex-direction: column; gap: var(--sp-2); }
.slot-frame {
  position: relative; flex: 1; min-height: 0; display: flex; align-items: flex-end; justify-content: center; overflow: hidden;
  background: radial-gradient(ellipse 80% 50% at 50% 100%, var(--gold-glow), transparent 70%), linear-gradient(180deg, var(--ink-900), var(--ink-860));
  border: 1px solid var(--band-edge-dim);
}
.slot-shade {
  height: 96%; aspect-ratio: 9 / 16; background: linear-gradient(180deg, var(--ink-600), var(--ink-780) 70%, var(--ink-820));
  -webkit-mask: var(--mask) bottom / contain no-repeat; mask: var(--mask) bottom / contain no-repeat;
}
.slot-art { height: 96%; aspect-ratio: 9 / 16; object-fit: contain; object-position: bottom; }
.slot[data-state="pending"] .slot-shade { animation: cp-breathe 2.4s ease-in-out infinite; }
@keyframes cp-breathe { 50% { opacity: 0.45; } }
.slot-pending { position: absolute; left: 0; right: 0; bottom: var(--sp-6); display: flex; align-items: center; justify-content: center; gap: var(--sp-2); color: var(--gold-300); font-size: var(--text-md); }
.slot-pending i { width: calc(16px * var(--u)); height: calc(16px * var(--u)); border-radius: 50%; border: 2px solid var(--ink-600); border-top-color: var(--gold-400); animation: cp-spin 1s linear infinite; }
@keyframes cp-spin { to { transform: rotate(360deg); } }
.slot-corner { position: absolute; width: calc(18px * var(--u)); height: calc(18px * var(--u)); border: solid var(--gold-500); }
.slot-corner--tl { top: -1px; left: -1px; border-width: 1px 0 0 1px; }
.slot-corner--br { right: -1px; bottom: -1px; border-width: 0 1px 1px 0; }
.slot-name { margin: var(--sp-1) 0 0; text-align: center; color: var(--gold-300); font: var(--text-xl) var(--f-display); letter-spacing: 0.14em; }
.slot[data-state="empty"] .slot-name { color: var(--paper-500); }
.slot-note { margin: 0; text-align: center; color: var(--paper-500); font-size: var(--text-xs); line-height: 1.6; }
.slot-cta { border-color: var(--gold-600); color: var(--gold-300); }

.region-title { display: flex; align-items: baseline; gap: var(--sp-3); margin: 0; color: var(--gold-400); font: 400 var(--text-xl) / 1.5 var(--f-display); letter-spacing: 0.08em; }
.region-title > span { color: var(--gold-500); font: var(--text-xs) var(--f-num); letter-spacing: 0.12em; }
.hint { margin: 0; color: var(--paper-400); font-size: var(--text-md); line-height: 1.8; }
.fields { display: grid; gap: var(--sp-3) var(--sp-4); }
.fields--two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.f--wide { grid-column: 1 / -1; }
.f { display: flex; flex-direction: column; gap: var(--sp-1); min-width: 0; color: var(--paper-400); font-size: var(--text-sm); }
.f-row { display: flex; gap: var(--sp-2); }
.f input, .f select, .f textarea, .ax-step input {
  box-sizing: border-box; width: 100%; min-width: 0; min-height: calc(40px * var(--u)); padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100); background: var(--ink-860); border: 1px solid var(--ink-600); border-radius: var(--radius-sm); font: var(--text-base) / 1.5 var(--f-sans);
}
.f textarea { resize: vertical; }
.f input:focus-visible, .f select:focus-visible, .f textarea:focus-visible { outline: none; border-color: var(--gold-500); box-shadow: var(--focus); }
.aff { display: flex; flex-wrap: wrap; gap: var(--sp-2) var(--sp-4); margin: 0; padding: var(--sp-2) var(--sp-3); border: 1px solid var(--band-edge-dim); border-radius: var(--radius-sm); font-size: var(--text-md); }
.aff legend { padding: 0 var(--sp-2); color: var(--paper-400); font-size: var(--text-sm); }
.aff label { display: inline-flex; align-items: center; gap: var(--sp-2); color: var(--paper-300); }
.aff input { width: calc(18px * var(--u)); height: calc(18px * var(--u)); margin: 0; accent-color: var(--gold-500); }
.alloc { display: grid; gap: var(--sp-3); }
.alloc--two { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--sp-4) var(--sp-8); align-content: start; }
.alloc-total { margin: 0; color: var(--paper-300); font-size: var(--text-md); font-variant-numeric: tabular-nums; }
.alloc-total b { color: var(--gold-300); font: var(--text-2xl) var(--f-serif); }
.ax { display: grid; grid-template-columns: minmax(0, 1fr) calc(136px * var(--u)); column-gap: var(--sp-3); align-items: center; }
.ax-label { color: var(--paper-100); font-size: var(--text-md); }
.ax-help { grid-column: 1; color: var(--paper-500); font-size: var(--text-xs); }
.ax-step { grid-column: 2; grid-row: 1 / 3; display: flex; gap: var(--sp-1); align-items: center; }
.ax-step input { padding: var(--sp-1); text-align: center; font-variant-numeric: tabular-nums; }
.ax-step .ui-icon-btn { flex: none; width: calc(32px * var(--u)); height: calc(36px * var(--u)); }
.ax-bar { grid-column: 1 / -1; height: calc(3px * var(--u)); margin-top: var(--sp-2); background: var(--ink-700); overflow: hidden; }
.ax-bar i { display: block; height: 100%; background: linear-gradient(90deg, var(--gold-600), var(--gold-400)); transform-origin: left; }

/* ── steps ── */
.steps { min-height: 0; display: flex; flex-direction: column; gap: var(--sp-5); max-width: calc(900px * var(--u)); }
.steps-rail { list-style: none; display: flex; gap: var(--sp-2); margin: 0; padding: 0; }
.steps-rail li { flex: 1; border-top: 2px solid var(--ink-600); }
.steps-rail li[data-done="true"] { border-color: var(--gold-600); }
.steps-rail li[data-on="true"] { border-color: var(--gold-400); }
.steps-rail button { display: flex; align-items: baseline; gap: var(--sp-3); width: 100%; padding: var(--sp-2) 0; border: 0; background: none; cursor: pointer; color: var(--paper-500); font: var(--text-xl) var(--f-display); letter-spacing: 0.08em; }
.steps-rail button span { font: var(--text-xs) var(--f-num); letter-spacing: 0.12em; }
.steps-rail button em { margin-left: auto; color: var(--paper-500); font: normal var(--text-xs) var(--f-sans); letter-spacing: 0.04em; }
.steps-rail li[data-on="true"] button { color: var(--gold-300); }
.steps-page { flex: 1; min-height: 0; overflow-y: auto; scrollbar-width: thin; }
.steps-nav { display: flex; justify-content: space-between; }
</style>
