import {mkdir,copyFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);
await mkdir(new URL('frontend/vendor/',root),{recursive:true});
for(const name of ['three.module.min.js','three.core.min.js'])await copyFile(new URL('node_modules/three/build/'+name,root),new URL('frontend/vendor/'+name,root));
await copyFile(new URL('node_modules/three/LICENSE',root),new URL('frontend/vendor/THREE-LICENSE.txt',root));
console.log('Local Three.js assets ready.');
