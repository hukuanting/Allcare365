// Node-only renderer for this axis-aligned vector mark. No image dependency required.
import { writeFile } from 'node:fs/promises';
import { deflateSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { BRAND_INK, BRAND_PAPER, BRAND_SIZE, BRAND_RECTS, BRAND_CENTRE } from '../src/config/brand.js';
const output = fileURLToPath(new URL('../public/', import.meta.url));
const scale = 0.72;
const offset = BRAND_SIZE * (1 - scale) / 2;
const rgb = hex => hex.slice(1).match(/../g).map(value => parseInt(value, 16));
const ink = rgb(BRAND_INK), paper = rgb(BRAND_PAPER);
const inside = (x, y, r) => x >= r.x && x < r.x + r.width && y >= r.y && y < r.y + r.height;
const mark = (x, y) => BRAND_RECTS.some(r => inside(x,y,r)) && !inside(x,y,BRAND_CENTRE);
function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) { crc ^= byte; for (let bit=0;bit<8;bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0); }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const name = Buffer.from(type), size = Buffer.alloc(4), crc = Buffer.alloc(4);
  size.writeUInt32BE(data.length); crc.writeUInt32BE(crc32(Buffer.concat([name,data])));
  return Buffer.concat([size,name,data,crc]);
}
function png(size) {
  const rows = Buffer.alloc(size * (size * 4 + 1));
  for (let y=0;y<size;y++) for (let x=0;x<size;x++) {
    let hits=0;
    for (let sy=0;sy<4;sy++) for (let sx=0;sx<4;sx++) {
      const mx=((x+(sx+.5)/4)*BRAND_SIZE/size-offset)/scale;
      const my=((y+(sy+.5)/4)*BRAND_SIZE/size-offset)/scale;
      if(mark(mx,my)) hits++;
    }
    const pixel=y*(size*4+1)+1+x*4;
    for(let c=0;c<3;c++) rows[pixel+c]=Math.round(ink[c]+(paper[c]-ink[c])*hits/16);
    rows[pixel+3]=255;
  }
  const header=Buffer.alloc(13);header.writeUInt32BE(size,0);header.writeUInt32BE(size,4);header[8]=8;header[9]=6;
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',deflateSync(rows)),chunk('IEND',Buffer.alloc(0))]);
}
const rect = (r, fill) => `<rect x="${r.x}" y="${r.y}" width="${r.width}" height="${r.height}" fill="${fill}"/>`;
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${BRAND_SIZE} ${BRAND_SIZE}"><rect width="${BRAND_SIZE}" height="${BRAND_SIZE}" fill="${BRAND_INK}"/><g transform="translate(${offset} ${offset}) scale(${scale})">${BRAND_RECTS.map(r=>rect(r,BRAND_PAPER)).join('')}${rect(BRAND_CENTRE,BRAND_INK)}</g></svg>\n`;
await writeFile(output+'favicon.svg',svg);
for (const [name,size] of [['apple-touch-icon.png',180],['logo192.png',192],['logo512.png',512]]) await writeFile(output+name,png(size));
const sizes=[16,32,48,64], images=sizes.map(png), directory=Buffer.alloc(6+16*sizes.length);
directory.writeUInt16LE(1,2);directory.writeUInt16LE(sizes.length,4);
let position=directory.length;
sizes.forEach((size,index)=>{const entry=6+16*index;directory[entry]=size;directory[entry+1]=size;directory.writeUInt16LE(1,entry+4);directory.writeUInt16LE(32,entry+6);directory.writeUInt32LE(images[index].length,entry+8);directory.writeUInt32LE(position,entry+12);position+=images[index].length;});
await writeFile(output+'favicon.ico',Buffer.concat([directory,...images]));
console.log('Generated AllCare365 SVG, ICO (16/32/48/64), Apple 180px and install 192/512px icons.');
