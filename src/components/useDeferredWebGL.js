import {useEffect} from 'react';

// Initialize decorative GPU effects after the first paint. Clean up even if
// a dialog is closed while the graphics module is still loading.
export default function useDeferredWebGL(setup,deps){
  useEffect(()=>{
    let cancelled=false,cleanup;
    const start=()=>import('./webgl-runtime').then(runtime=>{if(!cancelled)cleanup=setup(runtime)}).catch(()=>{});
    const idle=window.requestIdleCallback?.(start,{timeout:1500});
    const timer=idle===undefined?setTimeout(start,300):null;
    return()=>{cancelled=true;if(idle!==undefined)window.cancelIdleCallback(idle);if(timer!==null)clearTimeout(timer);cleanup?.()};
  },deps);
}
