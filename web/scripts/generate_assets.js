import fs from 'fs';
import path from 'path';
import zlib from 'zlib';

// Minimal pure Node.js PNG encoder
function createPNG(width, height, getPixel) {
  // RGB or RGBA raw rows: 1 byte filter type (0) + width * 4 bytes
  const rowSize = 1 + width * 4;
  const rawBuffer = Buffer.alloc(rowSize * height);

  for (let y = 0; y < height; y++) {
    const rowOffset = y * rowSize;
    rawBuffer[rowOffset] = 0; // Filter: None
    for (let x = 0; x < width; x++) {
      const [r, g, b, a] = getPixel(x, y, width, height);
      const pixelOffset = rowOffset + 1 + x * 4;
      rawBuffer[pixelOffset] = r;
      rawBuffer[pixelOffset + 1] = g;
      rawBuffer[pixelOffset + 2] = b;
      rawBuffer[pixelOffset + 3] = a !== undefined ? a : 255;
    }
  }

  const compressedData = zlib.deflateSync(rawBuffer);

  // PNG Signature
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  // Helper for CRC32
  function crc32(buf) {
    let c;
    const table = [];
    for (let n = 0; n < 256; n++) {
      c = n;
      for (let k = 0; k < 8; k++) {
        c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      }
      table[n] = c;
    }
    let crc = 0 ^ (-1);
    for (let i = 0; i < buf.length; i++) {
      crc = (crc >>> 8) ^ table[(crc ^ buf[i]) & 0xFF];
    }
    return (crc ^ (-1)) >>> 0;
  }

  function makeChunk(type, data) {
    const len = data.length;
    const buf = Buffer.alloc(12 + len);
    buf.writeUInt32BE(len, 0);
    buf.write(type, 4, 4, 'ascii');
    data.copy(buf, 8);
    const crcVal = crc32(buf.subarray(4, 8 + len));
    buf.writeUInt32BE(crcVal, 8 + len);
    return buf;
  }

  // IHDR chunk
  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8; // bit depth
  ihdrData[9] = 6; // color type RGBA
  ihdrData[10] = 0; // compression
  ihdrData[11] = 0; // filter
  ihdrData[12] = 0; // interlace
  const ihdrChunk = makeChunk('IHDR', ihdrData);

  // IDAT chunk
  const idatChunk = makeChunk('IDAT', compressedData);

  // IEND chunk
  const iendChunk = makeChunk('IEND', Buffer.alloc(0));

  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
}

const publicDir = path.resolve('./public');
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

// 1. Favicon 16x16
const fav16 = createPNG(16, 16, (x, y) => {
  if (x === 0 || x === 15 || y === 0 || y === 15) return [14, 15, 17, 255]; // #0E0F11
  // Amber signal light
  const dx = x - 8;
  const dy = y - 9;
  if (dx * dx + dy * dy <= 12) return [255, 178, 36, 255]; // #FFB224
  return [21, 23, 26, 255]; // #15171A
});
fs.writeFileSync(path.join(publicDir, 'favicon-16x16.png'), fav16);
fs.writeFileSync(path.join(publicDir, 'favicon.ico'), fav16);

// 2. Favicon 32x32
const fav32 = createPNG(32, 32, (x, y) => {
  if (x === 0 || x === 31 || y === 0 || y === 31) return [14, 15, 17, 255];
  const dx = x - 16;
  const dy = y - 18;
  if (dx * dx + dy * dy <= 36) return [255, 178, 36, 255];
  return [21, 23, 26, 255];
});
fs.writeFileSync(path.join(publicDir, 'favicon-32x32.png'), fav32);

// 3. Apple Touch Icon 180x180
const appleTouch = createPNG(180, 180, (x, y) => {
  // Border & dark background
  if (x < 8 || x > 171 || y < 8 || y > 171) return [14, 15, 17, 255];
  // Amber railway signal aspect
  const dx = x - 90;
  const dy = y - 105;
  if (dx * dx + dy * dy <= 1200) return [255, 178, 36, 255];
  return [21, 23, 26, 255];
});
fs.writeFileSync(path.join(publicDir, 'apple-touch-icon.png'), appleTouch);

// 4. Open Graph Image: 1200x630 per §13
// Composition: dark #0E0F11 bg, amber time-rule, platform gantt layout
const ogImage = createPNG(1200, 630, (x, y, w, h) => {
  // Border hairline
  if (x === 0 || x === w - 1 || y === 0 || y === h - 1) return [38, 40, 44, 255];

  // Amber time-rule vertical line at x = 750
  if (x >= 748 && x <= 751 && y >= 120 && y <= 550) {
    return [255, 178, 36, 255]; // #FFB224
  }

  // Gantt block representation on right half
  if (x >= 600 && x <= 1100 && y >= 120 && y <= 550) {
    const row = Math.floor((y - 120) / 45);
    const rowY = (y - 120) % 45;
    if (rowY >= 6 && rowY <= 38) {
      if (row === 1 && x >= 680 && x <= 920) return [62, 207, 142, 220]; // Green block #3ECF8E
      if (row === 2 && x >= 720 && x <= 880) return [240, 83, 58, 220]; // Red conflict block #F0533A
      if (row === 3 && x >= 620 && x <= 800) return [38, 40, 44, 255];
      if (row === 4 && x >= 820 && x <= 1040) return [38, 40, 44, 255];
      if (row === 5 && x >= 650 && x <= 950) return [62, 207, 142, 220];
      if (row === 6 && x >= 780 && x <= 1080) return [38, 40, 44, 255];
    }
    return [21, 23, 26, 255]; // Panel background
  }

  // Left card panel area
  if (x >= 80 && x <= 520 && y >= 120 && y <= 550) {
    return [21, 23, 26, 255]; // #15171A
  }

  // General dark background
  return [14, 15, 17, 255]; // #0E0F11
});
fs.writeFileSync(path.join(publicDir, 'og.png'), ogImage);

console.log('All static image assets successfully generated in public/ folder.');
