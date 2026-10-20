// Verify the new scalar solvers through the actual WASM JSON ABI, including
// conditional errors, fixed-background validation and ordered batches/sweeps.
import fs from 'node:fs';
import {JsonKernel} from '../../prototypes/rust-wasm/web/json-kernel.js';
const fixtures=JSON.parse(fs.readFileSync(process.argv[2]??'target/density-brent/wasm-fixtures.json'));
const bytes=fs.readFileSync('prototypes/rust-wasm/target/wasm32-unknown-unknown/release/glassure_prototype.wasm');
const {instance}=await WebAssembly.instantiate(bytes,{});
const kernel=new JsonKernel(instance.exports);
const equal=(a,b)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw Error('Ordered scalar batch/sweep differs from serial');};
let maxDensityDifference=0;
for(const row of fixtures){
 const result=kernel.call(row.request,'density_json');
 const actual=[result.density,result.density_error,result.background_scale,result.background_error];
 actual.forEach((value,i)=>{
  const expected=row.expected.fit[i];
  if(expected===null){if(value!==null)throw Error(row.case+' null error');return;}
  const rtol=[1,3].includes(i)?1e-3:1e-6;
  if(!Number.isFinite(value)||Math.abs(value-expected)>1e-5+rtol*Math.abs(expected))throw Error(row.case+' parameter '+i);
 });
 if(result.error_kind!=='conditional_standard_error')throw Error('Wrong scalar error semantics');
 if(Math.abs(result.sum_squared_residuals-row.expected.objective)>1e-14+1e-9*Math.abs(row.expected.objective))throw Error(row.case+' objective');
 maxDensityDifference=Math.max(maxDensityDifference,Math.abs(result.density-row.expected.fit[0]));
 if(row.request.algorithm==='lsq')continue;
 for(const invalid of [{...row.request,vary_background:true},{...row.request,max_evaluations:10}]){
  let rejected=false;
  try{kernel.call(invalid,'density_json');}catch(error){
   const expected=invalid.vary_background?'fixed background':'evaluation_budget';
   if(!error.message.includes(expected))throw error;
   rejected=true;
  }
  if(!rejected)throw Error('Invalid Brent request accepted');
 }
 const request=row.request;
 const invalid={...request,vary_background:true};
 const batch=kernel.call({jobs:[{operation:'density',request},{operation:'density',request:invalid},{operation:'density',request}],threads:1},'batch_json');
 equal(batch.items[0].output.result,result);equal(batch.items[2].output.result,result);
 if(batch.items[1].status!=='error')throw Error('Lost per-job scalar failure');
 const points=[{background_scale:.98},{background_scale:1.02}];
 const sweep=kernel.call({base:{operation:'density',request},points,threads:1},'sweep_json');
 points.forEach((point,i)=>{
  const c=structuredClone(request);Object.assign(c.calculation,point);
  equal(sweep.items[i].output.result,kernel.call(c,'density_json'));
 });
}
console.log(JSON.stringify({passed:true,scalar_cases:fixtures.length,max_density_difference:maxDensityDifference,ordered_batches_and_sweeps:true}));
