// Additional source-selection coverage through the actual WASM byte ABI.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {JsonKernel} from '../../prototypes/rust-wasm/web/json-kernel.js';
const root=new URL('../../',import.meta.url);
const bytes=fs.readFileSync(new URL('prototypes/rust-wasm/target/wasm32-unknown-unknown/release/glassure_prototype.wasm',root));
const {instance}=await WebAssembly.instantiate(bytes,{});
const kernel=new JsonKernel(instance.exports);
const cases=JSON.parse(fs.readFileSync(new URL('rust/fixtures/scattering-sources.json',root)));
let comparisons=0,maxError=0;
for(const row of cases){
 const actual=kernel.call(row.request,'factors_json');
 for(const [key,expected] of Object.entries(row.expected)){
  const a=Array.isArray(expected)?actual[key]:[actual[key]],e=Array.isArray(expected)?expected:[expected];
  assert.equal(a.length,e.length);
  a.forEach((value,i)=>{assert.ok(Number.isFinite(value)&&Math.abs(value-e[i])<=1e-10+1e-10*Math.abs(e[i]));maxError=Math.max(maxError,Math.abs(value-e[i]));comparisons++;});
 }
}
assert.throws(()=>kernel.call({composition:'SiO2',density:2.2,q:[0,1],source:'unsupported'},'factors_json'));
console.log(JSON.stringify({passed:true,sources:cases.map(c=>c.request.source),comparisons,maxError}));
