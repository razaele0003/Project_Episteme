import sharp from 'sharp';
import {mkdir} from 'node:fs/promises';
await mkdir('public', {recursive:true});
await sharp('src/assets/episteme-light.png').resize({width:600,withoutEnlargement:true}).webp({quality:90}).toFile('src/assets/episteme-light.webp');
await sharp('public/social-card.svg').png().toFile('public/social-card.png');
