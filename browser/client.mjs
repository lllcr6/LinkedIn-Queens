/** Worker-backed adapter matching the Python API used by the shared UI. */
let generation=null;
function worker(){return new Worker(new URL('./worker.mjs',import.meta.url),{type:'module'});}
export async function api(action,data) {
  if(action==='solve')return new Promise((resolve,reject)=>{
    const w=worker();w.onmessage=({data})=>{w.terminate();data.status==='error'?reject(new Error(data.message)):resolve(data);};
    w.onerror=e=>{w.terminate();reject(new Error(e.message||'Worker failed.'));};w.postMessage({action,data});
  });
  if(action==='generation/start') {
    generation?.worker.terminate();
    const job={id:crypto.randomUUID(),worker:worker(),started:performance.now(),result:null};generation=job;
    const finish=result=>{job.result={...result,elapsed_ms:performance.now()-job.started};job.worker.terminate();};
    job.worker.onmessage=({data})=>finish(data);
    job.worker.onerror=e=>finish({status:'error',message:e.message||'Worker failed.'});
    job.worker.postMessage({action:'generate',data});return {job_id:job.id};
  }
  if(!generation||generation.id!==data.job_id)throw new Error('Unknown generation job.');
  if(action==='generation/cancel'&&!generation.result) {
    generation.worker.terminate();generation.result={status:'cancelled',elapsed_ms:performance.now()-generation.started};
  }
  return generation.result||{status:'running',elapsed_ms:performance.now()-generation.started};
}
