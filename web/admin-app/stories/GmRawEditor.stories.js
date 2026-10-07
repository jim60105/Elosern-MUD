import GmRawEditor from '../components/GmRawEditor.vue';
export default {title:'GM/GmRawEditor',component:GmRawEditor,args:{target:'#7',raw:{attributes:[{key:'position',category:'state',value:{nested:[{'$ref':'#8',key:'測試房間'},true,3,null]}},{key:'position',category:'other',value:0}],tags:[{key:'marker',category:'flags'}],typeclass:'typeclasses.characters.PlayerCharacter',components:['read_only']},api:{get:async()=>({tick:42,baseline_tick:null,will_snapshot:true}),post:async()=>({target:'#7',state:{},snapshot:{taken:true,save_id:'20261007T090000-synthetic'}})}},play:async({canvasElement})=>{canvasElement.querySelector('button').click();}};
export const CategorySensitiveWarning={};
export const RefusedBatch={
  args:{api:{get:async()=>({tick:42,baseline_tick:null,will_snapshot:true}),post:async()=>{throw {code:'raw_edit_invalid',message:'原始資料批次不正確，未套用任何變更。',snapshot:{taken:true,save_id:'20261007T090000-synthetic'}};}}},
  play:async({canvasElement})=>{
    canvasElement.querySelector('button').click();
    await new Promise(resolve=>setTimeout(resolve,0));
    canvasElement.querySelector('section button').click();
    canvasElement.querySelector('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
    await new Promise(resolve=>setTimeout(resolve,0));
    [...canvasElement.querySelectorAll('button')].find(button=>button.textContent==='確認批次').click();
    await new Promise(resolve=>setTimeout(resolve,0));
    canvasElement.querySelector('[data-confirm]').click();
  },
};
