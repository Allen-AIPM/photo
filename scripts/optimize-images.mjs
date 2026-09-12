import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const data=JSON.parse(await fs.readFile(path.join(root,'src/data.json'),'utf8'));
const output=path.join(root,'public/optimized');
await fs.mkdir(output,{recursive:true});
const manifest={};
let originalBytes=0,thumbnailBytes=0;
for(const item of data.items){
  if(path.basename(item.file)!==item.file)throw new Error('Invalid image filename');
  const input=await fs.readFile(path.join(root,'public/image',item.file));
  const meta=await sharp(input).metadata();
  const width=meta.autoOrient?.width||meta.width,height=meta.autoOrient?.height||meta.height;
  const hash=crypto.createHash('sha256').update(input).update('webp-v1-q80').digest('hex').slice(0,12);
  const widths=[...new Set([Math.min(480,width),Math.min(960,width),Math.min(1440,width)])];
  const variants=[];
  for(const size of widths){
    const name=`${path.parse(item.file).name}-${hash}-${size}.webp`;
    const target=path.join(output,name);
    try {await fs.access(target)} catch {await sharp(input).rotate().resize({width:size,withoutEnlargement:true}).webp({quality:80,effort:5}).toFile(target)}
    variants.push({width:size,src:`/optimized/${name}`,bytes:(await fs.stat(target)).size});
  }
  manifest[item.file]={width,height,shape:width/height>1.05?'landscape':width/height<.95?'portrait':'square',originalBytes:input.length,variants};
  originalBytes+=input.length;thumbnailBytes+=variants[0].bytes;
}
await fs.writeFile(path.join(root,'src/image-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(`Images: ${data.items.length}; originals: ${originalBytes} bytes; small WebP: ${thumbnailBytes} bytes (${(100-thumbnailBytes/originalBytes*100).toFixed(1)}% less).`);
