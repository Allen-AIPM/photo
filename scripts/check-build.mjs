import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const dist=path.join(root,'dist');
const data=JSON.parse(await fs.readFile(path.join(root,'src/data.json'),'utf8'));
const images=JSON.parse(await fs.readFile(path.join(root,'src/image-manifest.json'),'utf8'));
async function walk(dir){const out=[];for(const e of await fs.readdir(dir,{withFileTypes:true})){const f=path.join(dir,e.name);out.push(...(e.isDirectory()?await walk(f):[f]))}return out}
assert((await fs.readFile(path.join(dist,'index.html'),'utf8')).includes('rel="preload"'),'Hero preload missing');
for(const item of data.items){assert(images[item.file]?.width>0);await fs.access(path.join(dist,'image',item.file));for(const v of images[item.file].variants)await fs.access(path.join(dist,v.src))}
const files=await walk(dist);
for(const file of files){
  assert((await fs.stat(file)).size<25*1024*1024,`File exceeds Cloudflare Pages limit: ${file}`);
  assert(!/perf-probe|perf-audit|API KEY|\.env/i.test(path.basename(file)),`Unexpected file in public output: ${file}`);
  if(/\.(js|html|css|json)$/.test(file)) {
    const text=await fs.readFile(file,'utf8');
    assert(!/C:\\\\Users|C:\\Users|127\.0\.0\.1:5173|localhost:5173/.test(text),`Local-only path in build: ${file}`);
  }
}
await fs.access(path.join(dist,'_headers'));
console.log(`PASS: ${data.items.length} originals and responsive variants; ${files.length} deployable files; preload, headers, file sizes and portable paths verified.`);
