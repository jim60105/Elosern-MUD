import GmConsoleResult from '../components/GmConsoleResult.vue';
export default {title:'GM/GmConsoleResult',component:GmConsoleResult};
export const SavedSuccess={args:{result:{target:'#7',snapshot:{taken:true,save_id:'20261007T090000-synthetic'},state:{wallet:30}}}};
export const NoSaveSuccess={args:{result:{target:'#7',snapshot:{taken:false,save_id:null},state:{wallet:30}}}};
export const RetainedSaveRefusal={args:{error:{code:'invalid_argument',message:'參數不正確，世界狀態未變更。',snapshot:{taken:true,save_id:'20261007T090000-synthetic'}}}};
export const CommittedProjectionWarning={args:{result:{target:'#7',snapshot:{taken:true,save_id:'20261007T090000-synthetic'},state:{error:{code:'state_projection_failed',message:'操作已完成，請重新整理。'}}}}};
