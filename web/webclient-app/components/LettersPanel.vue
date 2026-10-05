<script setup>
// A ruled correspondence folio, not a grid of web-form cards. Shared drawer
// chrome supplies the brass mounting; metadata recedes behind the letter text.
import { useLetters } from "../composables/use-letters.js";
const props = defineProps({ store: { type: Object, required: true } });
const { page, opened, message, recipient, body, locked, listPage, collect, read, send } = useLetters(props.store);
</script>

<template>
  <section class="letters-folio" aria-label="個人信件" data-testid="letters-panel">
    <!-- No reload control (correspondence-panel-open-once D1): the opening loads
         the first page once, and closing and reopening is the refresh boundary. -->
    <div v-if="page?.branch" class="letters-folio__tools">
      <button type="button" :disabled="locked" @click="collect()">領取來信</button>
    </div>
    <p class="letters-folio__notice" role="status">{{ message }}</p>
    <template v-if="page">
      <p v-if="!page.branch" class="letters-folio__muted">寄信與領信請前往銀羽驛站，已領取信件可隨身閱讀。</p>
      <div class="letters-folio__workspace">
        <div class="letters-folio__index" aria-label="已領取信件">
          <p v-if="!page.letters.length" class="letters-folio__muted">目前沒有已領取的信件。</p>
          <button v-for="letter in page.letters" :key="letter.source_id" type="button"
            class="letters-folio__letter" :disabled="locked" :aria-pressed="opened?.sourceId === letter.source_id"
            @click="read(letter.source_id)">
            <span>寄件人 #{{ letter.sender_id }}</span>
            <small>{{ letter.read_tick === null && opened?.sourceId !== letter.source_id ? '未讀' : '已讀' }}</small>
            <span class="letters-folio__id">{{ letter.source_id }}</span>
          </button>
          <button v-if="page.next !== null" type="button" :disabled="locked" @click="listPage(page.next)">下一頁</button>
        </div>
        <article v-if="opened" class="letters-folio__reading" aria-label="信件內容">
          <h3>來自 #{{ opened.senderId }}</h3>
          <p>{{ opened.body }}</p>
        </article>
        <p v-else class="letters-folio__muted">選擇一封信件閱讀，領取本身不會標記已讀。</p>
      </div>
      <form v-if="page.branch" class="letters-folio__compose" @submit.prevent="send()">
        <h3>寄出信件</h3>
        <label>收件人姓名或角色編號<input v-model="recipient" :disabled="locked" maxlength="255" placeholder="姓名或 #123" autocomplete="off" /></label>
        <label>信件內容<textarea v-model="body" :disabled="locked" rows="6" /></label>
        <div class="letters-folio__tools"><small>{{ Array.from(body).length }} / 8000 字</small><button type="submit" :disabled="locked">寄信</button></div>
      </form>
    </template>
  </section>
</template>

<style scoped>
.letters-folio { color: var(--paper-100); font-family: var(--f-sans); }
.letters-folio__tools { display: flex; align-items: center; gap: calc(18px * var(--ui-scale)); }
.letters-folio button { color: var(--paper-100); background: transparent; border: 0; border-bottom: 1px solid var(--band-edge-dim); padding: calc(9px * var(--ui-scale)); cursor: pointer; font-family: var(--f-serif); }
.letters-folio button:disabled { opacity: .5; cursor: default; }
.letters-folio__notice { min-height: 1.5em; color: var(--gold-400); }
.letters-folio__muted, .letters-folio small { color: var(--paper-500); font-size: var(--text-sm); }
.letters-folio__workspace { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); gap: calc(32px * var(--ui-scale)); }
.letters-folio__index { border-left: 1px solid var(--band-edge-dim); padding-left: calc(16px * var(--ui-scale)); }
.letters-folio__letter { display: grid; grid-template-columns: 1fr auto; width: 100%; text-align: left; gap: calc(8px * var(--ui-scale)); }
.letters-folio__letter[aria-pressed="true"] { border-bottom-color: var(--band-edge); color: var(--gold-400); }
.letters-folio__id { grid-column: 1 / -1; overflow-wrap: anywhere; color: var(--paper-500); font-family: var(--f-mono); font-size: var(--text-sm); }
.letters-folio h3 { font-family: var(--f-serif); font-weight: 500; }
.letters-folio__reading p { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.9; }
.letters-folio__compose { margin-top: calc(32px * var(--ui-scale)); border-top: 1px solid var(--band-edge-dim); }
.letters-folio label { display: grid; gap: calc(8px * var(--ui-scale)); margin-block: calc(18px * var(--ui-scale)); font-family: var(--f-serif); }
.letters-folio input, .letters-folio textarea { color: var(--paper-100); background: var(--panel); border: 0; border-bottom: 1px solid var(--band-edge-dim); padding: calc(12px * var(--ui-scale)); font: inherit; width: 100%; box-sizing: border-box; }
@media (max-width: 700px) { .letters-folio__workspace { grid-template-columns: 1fr; } }
</style>
