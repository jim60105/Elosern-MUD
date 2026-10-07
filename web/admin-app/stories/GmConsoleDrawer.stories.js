import GmConsoleDrawer from '../components/GmConsoleDrawer.vue';
const api={get:async()=>({tick:42,baseline_tick:42,will_snapshot:false}),post:async()=>({target:'#7',state:{wallet:30},snapshot:{taken:false,save_id:null}})};
export default {title:'GM/GmConsoleDrawer',component:GmConsoleDrawer,args:{kind:'characters',target:'#7',api},play:async({canvasElement})=>{canvasElement.querySelector('button').click();}};
export const Character={};
export const Monster={args:{kind:'monsters'}};
export const Room={args:{kind:'rooms'}};
export const RefusedWrite={
  args:{api:{...api,post:async()=>{throw {code:'invalid_argument',message:'參數不正確，世界狀態未變更。',snapshot:{taken:false,save_id:null}};}}},
  play:async({canvasElement})=>{
    canvasElement.querySelector('button').click();
    await new Promise(resolve=>setTimeout(resolve,0));
    const select=canvasElement.querySelector('select');
    select.value='set_wallet'; select.dispatchEvent(new Event('change',{bubbles:true}));
    await new Promise(resolve=>setTimeout(resolve,0));
    const input=canvasElement.querySelector('input');
    input.value='-1'; input.dispatchEvent(new Event('input',{bubbles:true}));
    canvasElement.querySelector('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
    await new Promise(resolve=>setTimeout(resolve,0));
    canvasElement.querySelector('[data-confirm]').click();
  },
};
