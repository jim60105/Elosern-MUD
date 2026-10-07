import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import GmConsoleDrawer from '../components/GmConsoleDrawer.vue';
import GmConsolePrompt from '../components/GmConsolePrompt.vue';
import GmRawEditor from '../components/GmRawEditor.vue';
import GmConsoleResult from '../components/GmConsoleResult.vue';
import WorldPanel from '../views/overview/WorldPanel.vue';
import GmEntityView from '../components/GmEntityView.vue';
import { NPC_DETAIL } from './runtime-helpers.js';
import { GmApiError } from '../lib/api.js';
import { KIND_VERBS, VERB_FIELDS, argumentsFor, saveNotice } from '../lib/console.js';

const status = { tick:42, baseline_tick:null, will_snapshot:true };
const saved = { target:'#7', state:{wallet:3}, snapshot:{taken:true,save_id:'actual-save'} };
const request = {path:'/console/set_wallet',body:{target:'#7',copper:3},label:'set_wallet · #7'};
function api(options={}) { return {get:vi.fn(async()=>status),post:vi.fn(async()=>saved),...options}; }
function render(component,props) { return mount(component,{props,attachTo:document.body}); }
function button(wrapper,text) { return wrapper.findAll('button').find(node=>node.text()===text); }
afterEach(()=>{ document.body.innerHTML=''; document.documentElement.classList.remove('gm-scroll-locked'); });

describe('closed contextual console vocabulary',()=>{
  it('has exactly fourteen verbs with kind-appropriate forms and numeric arguments',async()=>{
    expect(Object.keys(VERB_FIELDS)).toHaveLength(14);
    for (const [kind,verbs] of Object.entries(KIND_VERBS)) {
      const wrapper=render(GmConsoleDrawer,{kind,target:'#7',api:api()});
      await button(wrapper,'主控台').trigger('click');
      expect(wrapper.findAll('option').map(node=>node.element.value)).toEqual(verbs);
      for (const verb of verbs) {
        await wrapper.get('select').setValue(verb);
        expect(wrapper.findAll('input').map(node=>node.attributes('name'))).toEqual(VERB_FIELDS[verb]);
      }
      await wrapper.get('aside').trigger('keydown',{key:'Escape'});
      expect(wrapper.find('aside').exists()).toBe(false);
      wrapper.unmount();
    }
    expect(argumentsFor('give_item','#7',{key:'t_item',quantity:'2'})).toEqual({target:'#7',key:'t_item',quantity:2});
    expect(argumentsFor('spawn_monster','#8',{species:'t_species',variant:'t_variant'})).toEqual({room:'#8',species:'t_species',variant:'t_variant'});
    expect(argumentsFor('advance_clock','#7',{seconds:'0'})).toEqual({seconds:0});
    const npc=render(GmConsoleDrawer,{kind:'npcs',target:'#7',api:api()});
    expect(npc.find('button').exists()).toBe(false);
  });
  it('submits numeric contextual form only after fresh status and confirmation then refreshes',async()=>{
    const client=api();
    const wrapper=render(GmConsoleDrawer,{kind:'characters',target:'#7',api:client});
    await button(wrapper,'主控台').trigger('click');
    await wrapper.get('select').setValue('set_wallet');
    await wrapper.get('input').setValue('3');
    await wrapper.get('form').trigger('submit');
    await flushPromises();
    expect(client.get).toHaveBeenCalledWith('/console/status');
    expect(client.post).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('首次介入');
    await wrapper.get('[data-confirm]').trigger('click'); await flushPromises();
    expect(client.post).toHaveBeenCalledWith('/console/set_wallet',{target:'#7',copper:3});
    expect(wrapper.emitted('done')[0]).toEqual([saved]);
    expect(wrapper.text()).toContain('actual-save');
  });
});

describe('actual save confirmation and result',()=>{
  it('renders actual saved outcome over a stale no-save preview without sending a client baseline',async()=>{
    const client=api({get:vi.fn(async()=>({tick:42,baseline_tick:42,will_snapshot:false}))});
    const wrapper=render(GmConsolePrompt,{request,api:client}); await flushPromises();
    expect(wrapper.get('[data-save-notice]').text()).toContain('本次不另存檔');
    await wrapper.get('[data-confirm]').trigger('click'); await flushPromises();
    expect(client.post).toHaveBeenCalledWith(request.path,request.body);
    expect(wrapper.text()).toContain('actual-save');
  });
  it.each([
    [status,'首次介入'],
    [{tick:42,baseline_tick:42,will_snapshot:false},'本次不另存檔'],
    [{tick:43,baseline_tick:42,will_snapshot:true},'時間已變更'],
    [{tick:41,baseline_tick:42,will_snapshot:true},'時間已變更'],
  ])('uses authoritative status without guessing from wall time',async(value,notice)=>{
    const client=api({get:vi.fn(async()=>value)});
    const wrapper=render(GmConsolePrompt,{request,api:client}); await flushPromises();
    expect(wrapper.get('[data-save-notice]').text()).toContain(notice);
    expect(client.post).not.toHaveBeenCalled();
    await button(wrapper,'取消').trigger('click');
    expect(wrapper.emitted('cancel')).toHaveLength(1);
    expect(client.post).not.toHaveBeenCalled();
  });
  it('blocks pending status, absent clock, and status failures',async()=>{
    let resolve;
    const client=api({get:vi.fn(()=>new Promise(done=>{resolve=done;}))});
    const wrapper=render(GmConsolePrompt,{request,api:client});
    expect(wrapper.get('[data-confirm]').element.disabled).toBe(true);
    resolve({tick:null,baseline_tick:null,will_snapshot:true}); await flushPromises();
    expect(wrapper.text()).toContain('世界時鐘尚未建立');
    expect(wrapper.get('[data-confirm]').element.disabled).toBe(true);
    await wrapper.setProps({request:{...request}}); client.get.mockRejectedValueOnce(new GmApiError('network_error',{message:'無法連線。'}));
    await wrapper.setProps({request:{...request}}); await flushPromises();
    expect(wrapper.get('[data-confirm]').element.disabled).toBe(true);
    expect(client.post).not.toHaveBeenCalled();
  });
  it('prevents duplicate submission and shows truthful retained-save refusal',async()=>{
    let reject;
    const client=api({post:vi.fn(()=>new Promise((_resolve,fail)=>{reject=fail;}))});
    const wrapper=render(GmConsolePrompt,{request,api:client}); await flushPromises();
    const confirm=wrapper.get('[data-confirm]');
    await confirm.trigger('click'); await confirm.trigger('click');
    expect(client.post).toHaveBeenCalledTimes(1);
    expect(button(wrapper,'取消').element.disabled).toBe(true);
    reject(new GmApiError('invalid_argument',{message:'參數不正確。',snapshot:{taken:true,save_id:'retained-save'}})); await flushPromises();
    expect(wrapper.text()).toContain('invalid_argument');
    expect(wrapper.text()).toContain('retained-save');
    expect(wrapper.emitted('done')).toBeUndefined();
  });
  it('renders no-save success and committed projection warning',()=>{
    const wrapper=render(GmConsoleResult,{result:{...saved,snapshot:{taken:false,save_id:null},state:{error:{code:'state_projection_failed',message:'操作已完成，請重新整理。'}}}});
    expect(wrapper.text()).toContain('本次未建立介入前存檔');
    expect(wrapper.text()).toContain('操作已完成，請重新整理');
    expect(saveNotice(null)).toContain('正在確認');
  });
});

describe('ordered category-sensitive raw editing',()=>{
  it('refreshes both curated and raw state and retains the result after the editor remounts',async()=>{
    let mutated=false;
    const client=api({
      get:vi.fn(async path=>{
        if(path==='/console/status')return status;
        if(path==='/state/npcs/12')return {...NPC_DETAIL,label:mutated?'合成更新':NPC_DETAIL.label};
        if(path==='/state/object/12/raw')return {raw:{attributes:[],tags:[]}};
        throw new Error(path);
      }),
      post:vi.fn(async()=>{mutated=true;return saved;}),
    });
    const wrapper=render(GmEntityView,{kind:'npcs',id:'12',api:client}); await flushPromises();
    await wrapper.findAll('[role=\"tab\"]')[1].trigger('click'); await flushPromises();
    await button(wrapper,'編輯').trigger('click');
    await wrapper.get('section[aria-label=\"原始資料編輯\"] input').setValue('t_notes');
    await wrapper.get('section[aria-label=\"原始資料編輯\"] form').trigger('submit');
    await button(wrapper,'確認批次').trigger('click'); await flushPromises();
    await wrapper.get('[data-confirm]').trigger('click'); await flushPromises();
    expect(client.get.mock.calls.filter(([path])=>path==='/state/npcs/12')).toHaveLength(2);
    expect(client.get.mock.calls.filter(([path])=>path==='/state/object/12/raw')).toHaveLength(2);
    expect(wrapper.text()).toContain('合成更新');
    expect(wrapper.text()).toContain('actual-save');
    expect(button(wrapper,'編輯')).toBeDefined();
  });
  it('preserves refs/primitives and warning, then posts the batch and refreshes',async()=>{
    const client=api();
    const raw={attributes:[{key:'position',category:'state',value:{nested:[{'$ref':'#8'},false,3,null]}}],tags:[{key:'marker',category:'flags'}],typeclass:'typeclasses.objects.Object',components:['read_only']};
    const wrapper=render(GmRawEditor,{target:'#7',raw,api:client});
    await button(wrapper,'編輯').trigger('click');
    expect(wrapper.get('[role="note"]').text()).toContain('繞過規則層');
    expect(wrapper.findAll('option').map(node=>node.text())).toEqual(['set_attr','del_attr','add_tag','remove_tag','set_location']);
    await button(wrapper,'state · position').trigger('click');
    await wrapper.get('form').trigger('submit');
    await button(wrapper,'flags · marker').trigger('click');
    await wrapper.get('form').trigger('submit');
    await wrapper.get('select').setValue('set_location');
    await wrapper.get('textarea').setValue('null');
    await wrapper.get('form').trigger('submit');
    expect(wrapper.get('[role="note"]').exists()).toBe(true);
    await button(wrapper,'確認批次').trigger('click'); await flushPromises();
    await wrapper.get('[data-confirm]').trigger('click'); await flushPromises();
    expect(client.post).toHaveBeenCalledWith('/state/object/7/raw',{operations:[{op:'set_attr',key:'position',category:'state',value:raw.attributes[0].value},{op:'remove_tag',key:'marker',category:'flags'},{op:'set_location',value:null}]});
    expect(wrapper.emitted('done')).toHaveLength(1);
    expect(wrapper.findAll('ol li')).toHaveLength(0);
  });
  it('invalid JSON and cancelled confirmation never post',async()=>{
    const client=api(); const wrapper=render(GmRawEditor,{target:'#7',raw:{},api:client});
    await button(wrapper,'編輯').trigger('click'); await wrapper.get('textarea').setValue('{'); await wrapper.get('form').trigger('submit');
    expect(wrapper.get('[role="alert"]').text()).toContain('JSON');
    expect(wrapper.findAll('ol li')).toHaveLength(0);
    await wrapper.get('textarea').setValue('true'); await wrapper.get('form').trigger('submit');
    await button(wrapper,'確認批次').trigger('click'); await flushPromises(); await button(wrapper,'取消').trigger('click');
    expect(client.post).not.toHaveBeenCalled();
  });
});

describe('dashboard clock intervention',()=>{
  it('confirms numeric seconds and requests one world refresh without creating a timer',async()=>{
    const client=api();
    const timer=vi.spyOn(globalThis,'setInterval');
    const wrapper=mount(WorldPanel,{props:{world:{clock:{tick:42,year:1,season:'春',day:1,hour:0,minute:0},sessions:0,accounts:0,active_combats:0,live_instances:0}},global:{provide:{gmApi:client}},attachTo:document.body});
    await wrapper.get('input').setValue('5'); await wrapper.get('form').trigger('submit'); await flushPromises();
    await wrapper.get('[data-confirm]').trigger('click'); await flushPromises();
    expect(client.post).toHaveBeenCalledWith('/console/advance_clock',{seconds:5});
    expect(wrapper.emitted('refresh')).toHaveLength(1);
    expect(timer).not.toHaveBeenCalled();
    await wrapper.setProps({world:{clock:null}});
    expect(button(wrapper,'推進時鐘').element.disabled).toBe(true);
    timer.mockRestore();
  });
});
