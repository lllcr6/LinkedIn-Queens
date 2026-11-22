import {solve,generate,SearchLimit} from './engine.mjs';
self.onmessage=({data})=>{
  try { self.postMessage(data.action==='solve'?solve(data.data.regions,data.data.solver):generate(data.data)); }
  catch(error){self.postMessage({status:error instanceof SearchLimit?'limit':'error',message:error.message});}
};
