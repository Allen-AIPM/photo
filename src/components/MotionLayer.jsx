import React, {useEffect, useState} from 'react';
import {createPortal} from 'react-dom';
import TargetCursor from './TargetCursor';
import GlowCursor from './GlowCursor';

export function useMotionEnabled(){
  const [enabled,setEnabled]=useState(()=>!window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(()=>{const media=window.matchMedia('(prefers-reduced-motion: reduce)');const update=()=>setEnabled(!media.matches);media.addEventListener('change',update);return()=>media.removeEventListener('change',update)},[]);
  return enabled;
}

export default function MotionLayer({modalOpen}){
  const enabled=useMotionEnabled();
  const [fine,setFine]=useState(()=>window.matchMedia('(hover: hover) and (pointer: fine)').matches);
  const [host,setHost]=useState(document.body);
  useEffect(()=>{const media=window.matchMedia('(hover: hover) and (pointer: fine)');const update=()=>setFine(media.matches);media.addEventListener('change',update);return()=>media.removeEventListener('change',update)},[]);
  useEffect(()=>{const frame=requestAnimationFrame(()=>setHost(document.querySelector('dialog[open]')||document.body));return()=>cancelAnimationFrame(frame)},[modalOpen]);
  if(!enabled||!fine)return null;
  return <><TargetCursor key={modalOpen?'modal':'page'} portalRoot={host} targetSelector="button:not(:disabled), a[href], .stack-card[tabindex='0']" cursorColor="#c96a45" cursorColorOnTarget="#af5230" hideDefaultCursor={false} spinDuration={4} parallaxOn={false}/>{createPortal(<GlowCursor key={modalOpen?'modal':'page'} className="page-glow" color="#d6884a" secondaryColor="#c96a45" trailLength={24} trailWidth={3} glowIntensity={.7} glowSpread={.65} hotspot={.15} brightness={.85} opacity={.48} followSpeed={.25} idleTimeout={180} fadeDuration={450} blendMode="normal" maxDevicePixelRatio={1} aria-hidden="true"/>,host)}</>;
}
