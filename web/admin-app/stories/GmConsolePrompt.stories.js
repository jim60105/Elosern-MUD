import GmConsolePrompt from '../components/GmConsolePrompt.vue';
const request={path:'/console/set_wallet',body:{target:'#7',copper:30},label:'set_wallet · #7'};
const result={target:'#7',snapshot:{taken:true,save_id:'20261007T090000-synthetic'},state:{wallet:30}};
function client(status,refusal=null){return {get:async()=>status,post:async()=>{if(refusal)throw refusal;return result;}};}
export default {title:'GM/GmConsolePrompt',component:GmConsolePrompt,args:{request,api:client({tick:42,baseline_tick:null,will_snapshot:true})}};
export const FirstIntervention={};
export const UnchangedTick={args:{api:client({tick:42,baseline_tick:42,will_snapshot:false})}};
export const ChangedTick={args:{api:client({tick:43,baseline_tick:42,will_snapshot:true})}};
export const MissingClock={args:{api:client({tick:null,baseline_tick:null,will_snapshot:true})}};
export const Success={play:async({canvasElement})=>{await new Promise(resolve=>setTimeout(resolve,0));canvasElement.querySelector('[data-confirm]').click();}};
export const Refusal={args:{api:client({tick:42,baseline_tick:null,will_snapshot:true},{code:'snapshot_failed',message:'另一項存檔或主控台操作正在進行。',snapshot:{taken:false,save_id:null}})},play:async({canvasElement})=>{await new Promise(resolve=>setTimeout(resolve,0));canvasElement.querySelector('[data-confirm]').click();}};
