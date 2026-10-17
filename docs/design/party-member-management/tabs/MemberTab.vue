<script setup>
// Approved visual prototype (party member management §6.1): the 成員 tab.
// Portrait nameplate plus relation and identity. No rule explanations: the
// follow rules live in the help overlay.
import { computed, ref, watch } from "vue";
import PmGlyph from "../PmGlyph.vue";
import { INVITE, MEMBER_DETAIL, MEMBERS } from "../prototype-data.js";

const props = defineProps({ memberId: { type: [Number, String], required: true } });

const member = computed(() => MEMBERS.find((m) => m.id === props.memberId) ?? null);
const detail = computed(() => (member.value ? MEMBER_DETAIL[member.value.id] : null));
const leaveArmed = ref(false);
watch(() => props.memberId, () => { leaveArmed.value = false; });

function pct([cur, max]) {
  return `${max ? Math.round((cur / max) * 100) : 0}%`;
}
</script>

<template>
  <template v-if="member">
    <div class="pm-col pm-list mt-portrait">
      <div class="mt-art" :class="{ 'is-ko': member.knocked_out }">
        <img :src="member.art" alt="" />
      </div>
      <h3 class="mt-name">{{ member.name }}</h3>
      <p class="mt-title">{{ member.title }}</p>
      <div class="pm-gauge"><span style="color: var(--vit-hp)">HP</span><span class="pm-gauge__track"><i :style="{ width: pct(member.hp), background: 'var(--vit-hp)' }" /></span><span class="pm-gauge__value">{{ member.hp[0] }} / {{ member.hp[1] }}</span></div>
      <div class="pm-gauge"><span style="color: var(--vit-mp)">MP</span><span class="pm-gauge__track"><i :style="{ width: pct(member.mp), background: 'var(--vit-mp)' }" /></span><span class="pm-gauge__value">{{ member.mp[0] }} / {{ member.mp[1] }}</span></div>
      <div class="pm-gauge"><span style="color: var(--vit-sp)">SP</span><span class="pm-gauge__track"><i :style="{ width: pct(member.sp), background: 'var(--vit-sp)' }" /></span><span class="pm-gauge__value">{{ member.sp[0] }} / {{ member.sp[1] }}</span></div>
    </div>

    <div class="pm-col pm-detail">
      <div class="pm-detail__scroll">
        <template v-if="member.commander">
          <div class="pm-sech">人物設定</div>
          <div v-for="p in detail.persona" :key="p.label" class="mt-letter">
            <b>{{ p.label }}</b>{{ p.text }}
          </div>
        </template>
        <template v-else>
          <div class="pm-sech">羈絆</div>
          <div class="mt-bond">
            <span class="mt-bond__stage">{{ detail.bond.stage }}</span>
            <span class="mt-pips" :aria-label="`第 ${detail.bond.step} 階，共 ${detail.bond.steps} 階`">
              <i v-for="n in detail.bond.steps" :key="n" :class="{ 'is-on': n <= detail.bond.step }" />
            </span>
          </div>
          <div class="pm-sech">同行身分</div>
          <div class="mt-tags">
            <span v-if="detail.membership.general" class="pm-tag">一般同伴</span>
            <span v-for="c in detail.membership.commissions" :key="c" class="pm-tag pm-tag--seal">委託：{{ c }}</span>
          </div>
        </template>
        <div class="pm-sech">親密狀態</div>
        <div class="mt-intim">
          <div v-for="i in detail.intimate" :key="i.label"><span>{{ i.label }}</span><b>{{ i.value }}</b></div>
        </div>
      </div>

      <div class="pm-bar">
        <template v-if="member.commander">
          <button type="button" class="pm-btn pm-btn--gold">編輯人物設定</button>
        </template>
        <template v-else-if="leaveArmed">
          <span class="pm-bar__reason pm-bar__reason--warn">{{ member.name }}會離開隊伍。</span>
          <button type="button" class="pm-btn" @click="leaveArmed = false">取消</button>
          <button type="button" class="pm-btn pm-btn--primary">確認請其離隊</button>
        </template>
        <template v-else>
          <button type="button" class="pm-btn pm-btn--ghost" style="margin-right: auto" @click="leaveArmed = true">請其離隊…</button>
          <button type="button" class="pm-btn pm-btn--gold">人物卡</button>
          <button v-if="member.knocked_out" type="button" class="pm-btn" aria-disabled="true" title="倒地的同伴無法附身">附身</button>
          <button v-else type="button" class="pm-btn pm-btn--primary">{{ detail.possessed ? "解除附身" : "附身" }}</button>
        </template>
      </div>
    </div>
  </template>

  <template v-else>
    <div class="pm-col pm-list mt-portrait">
      <div class="mt-art mt-art--empty"><PmGlyph name="plus" /></div>
      <h3 class="mt-name">空位</h3>
    </div>
    <div class="pm-col pm-detail">
      <div class="pm-detail__scroll">
        <div class="pm-sech">可邀請</div>
        <div class="mt-invite"><span class="pm-avatar pm-avatar--sm">蜜</span>{{ INVITE.target }}</div>
      </div>
      <div class="pm-bar">
        <span class="pm-bar__reason">{{ INVITE.reason }}</span>
        <button type="button" class="pm-btn" :aria-disabled="!INVITE.enabled">邀請同行</button>
      </div>
    </div>
  </template>
</template>

<style scoped>
.mt-portrait { display: flex; flex-direction: column; }
.mt-art {
  position: relative;
  flex: 1;
  min-height: calc(220px * var(--ui-scale));
  margin-bottom: var(--sp-3);
  border: 1px solid var(--pm-line);
  border-radius: var(--radius-sm);
  background: linear-gradient(180deg, #3a3329, #15171c 80%);
  overflow: hidden;
  display: grid;
  place-items: end center;
}
.mt-art img { width: 100%; height: 100%; object-fit: cover; object-position: top center; opacity: 0.9; }
.mt-art.is-ko img { filter: grayscale(0.8) brightness(0.6); }
.mt-art--empty { place-items: center; color: var(--paper-700); font-size: calc(48px * var(--ui-scale)); border-style: dashed; background: none; }
.mt-name { margin: 0; color: var(--paper-50); font: var(--text-2xl) var(--f-display); }
.mt-title { margin: 2px 0 var(--sp-2); color: var(--gold-400); font-size: var(--text-xs); }
.mt-letter {
  margin-bottom: var(--sp-2);
  padding: var(--sp-2) var(--sp-4);
  border-left: 2px solid var(--gold-600);
  background: rgba(0, 0, 0, 0.18);
  color: var(--paper-200);
  font: var(--text-md) / 1.85 var(--f-serif);
}
.mt-letter b { display: block; color: var(--gold-400); font: 500 var(--text-xs) var(--f-sans); letter-spacing: 0.1em; }
.mt-bond { display: flex; align-items: center; gap: var(--sp-4); }
.mt-bond__stage { color: var(--paper-50); font: var(--text-xl) var(--f-display); }
.mt-pips { display: flex; gap: var(--sp-1); }
.mt-pips i { width: calc(22px * var(--ui-scale)); height: calc(8px * var(--ui-scale)); transform: skewX(-20deg); background: #2a2c30; }
.mt-pips i.is-on { background: var(--gold-500); box-shadow: 0 0 6px var(--gold-glow); }
.mt-tags .pm-tag { margin: 0 var(--sp-2) 0 0; padding: 2px var(--sp-2); font-size: var(--text-xs); color: var(--paper-200); border-color: var(--pm-line); }
.mt-tags .pm-tag--seal { color: var(--seal-400); border-color: var(--seal-700); }
.mt-intim { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--sp-2); }
.mt-intim div { padding: var(--sp-2) var(--sp-3); border: 1px solid var(--pm-line); border-radius: var(--radius-sm); color: var(--paper-500); font-size: var(--text-xs); }
.mt-intim b { display: block; color: var(--pm-intimate); font: 500 var(--text-md) var(--f-sans); }
.mt-invite { display: flex; align-items: center; gap: var(--sp-2); color: var(--paper-100); }
</style>
