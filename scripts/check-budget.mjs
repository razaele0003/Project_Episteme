import {readdir,stat,readFile} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import assert from 'node:assert/strict';
let javascript=0,css=0;
for(const name of await readdir('dist/assets')){
  const data=await readFile('dist/assets/'+name);
  if(name.endsWith('.js')) javascript+=gzipSync(data).length;
  if(name.endsWith('.css')) css+=gzipSync(data).length;
}
assert(javascript<110000,`JavaScript gzip budget exceeded: ${javascript}`);
assert(css<20000,`CSS gzip budget exceeded: ${css}`);
assert((await stat('src/assets/episteme-light.webp')).size<40000);
assert((await stat('public/social-card.png')).size<150000);
console.log({javascriptGzip:javascript,cssGzip:css,result:'budgets passed'});
