import React, {useContext} from 'react';
import manifest from '../image-manifest.json';
import StackActiveContext from './StackActiveContext';

export default function OptimizedImage({item,hero=false,priority=false,detail=false,...props}){
  const stackActive=useContext(StackActiveContext);
  const image=manifest[item.file];
  if(!image)return <img src={'/image/'+encodeURIComponent(item.file)} alt={item.title} {...props}/>;
  const variants=hero&&!stackActive?[image.variants[0]]:image.variants;
  return <img src={variants[hero?Math.min(1,variants.length-1):detail?variants.length-1:0].src}
    srcSet={variants.map(v=>`${v.src} ${v.width}w`).join(', ')}
    sizes={hero?'(max-width: 800px) 80vw, (min-width: 1800px) 650px, 40vw':detail?'(max-width: 800px) 90vw, 600px':'(min-width: 1796px) 323px, (min-width: 1500px) 18vw, (min-width: 1051px) 23vw, (min-width: 801px) 30vw, 45vw'}
    width={image.width} height={image.height} alt={item.title}
    loading={priority||hero||detail?'eager':'lazy'} fetchPriority={priority?'high':hero?'low':'auto'} decoding="async" {...props}/>;
}
