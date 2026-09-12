import {defineConfig} from 'vite';
import fs from 'node:fs';

export default defineConfig({
  plugins:[{
    name:'preload-hero-image',
    transformIndexHtml(){
      const data=JSON.parse(fs.readFileSync(new URL('./src/data.json',import.meta.url),'utf8'));
      const images=JSON.parse(fs.readFileSync(new URL('./src/image-manifest.json',import.meta.url),'utf8'));
      const hero=images[data.items[1].file].variants;
      return [{tag:'link',attrs:{rel:'preload',as:'image',href:hero[Math.min(1,hero.length-1)].src,imagesrcset:hero.map(v=>`${v.src} ${v.width}w`).join(', '),imagesizes:'(max-width: 800px) 80vw, (min-width: 1800px) 650px, 40vw',fetchpriority:'high'},injectTo:'head'}];
    }
  }],
  build:{rollupOptions:{
    onwarn(warning,warn){if(warning.code==='MODULE_LEVEL_DIRECTIVE'&&warning.message.includes('use client'))return;warn(warning)},
    output:{manualChunks(id){if(id.endsWith('/components/webgl-runtime.js'))return 'webgl';if(id.includes('node_modules')){if(/[/\\](react|react-dom|scheduler)[/\\]/.test(id))return 'react-vendor';if(id.includes('gsap'))return 'text-motion';if(/[/\\](motion|framer-motion|motion-dom|motion-utils)[/\\]/.test(id))return 'stack-motion';if(id.includes('/ogl/'))return 'webgl';}}}
  }}
});
