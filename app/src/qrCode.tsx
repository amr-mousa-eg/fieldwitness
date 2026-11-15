/**
 * Zero-dependency deterministic ISO/IEC 18004 QR Code (Byte mode, Error Correction Level L, Versions 1–10).
 * Used cleanly in PrintDossier so farmers and extension agronomists can scan paper dossiers back to exact URLs.
 */

const GF_EXP = new Uint8Array(512);
const GF_LOG = new Uint8Array(256);

(() => {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    GF_EXP[i] = x;
    GF_LOG[x] = i;
    x <<= 1;
    if (x & 0x100) x ^= 0x11d;
  }
  for (let i = 255; i < 512; i++) GF_EXP[i] = GF_EXP[i - 255];
})();

function gfMul(a: number, b: number): number {
  return a === 0 || b === 0 ? 0 : GF_EXP[GF_LOG[a] + GF_LOG[b]];
}

function rsGenerator(degree: number): Uint8Array {
  let poly = new Uint8Array([1]);
  for (let i = 0; i < degree; i++) {
    const next = new Uint8Array(poly.length + 1);
    const factor = GF_EXP[i];
    for (let j = 0; j < poly.length; j++) {
      next[j] ^= poly[j];
      next[j + 1] ^= gfMul(poly[j], factor);
    }
    poly = next;
  }
  return poly;
}

function rsEncode(data: Uint8Array, ecCount: number): Uint8Array {
  const gen = rsGenerator(ecCount);
  const res = new Uint8Array(data.length + ecCount);
  res.set(data);
  for (let i = 0; i < data.length; i++) {
    const lead = res[i];
    if (lead === 0) continue;
    for (let j = 0; j < gen.length; j++) {
      res[i + j] ^= gfMul(gen[j], lead);
    }
  }
  return res.slice(data.length);
}

interface VersionSpec {
  version: number;
  totalDataCodewords: number;
  ecPerBlock: number;
  blocksGroup1: number;
  dataGroup1: number;
  blocksGroup2: number;
  dataGroup2: number;
  alignment: number[];
}

// ISO 18004 EC Level L tables for Versions 1..10 (up to 271 UTF-8 bytes)
const VERSIONS: VersionSpec[] = [
  { version: 1, totalDataCodewords: 19, ecPerBlock: 7, blocksGroup1: 1, dataGroup1: 19, blocksGroup2: 0, dataGroup2: 0, alignment: [] },
  { version: 2, totalDataCodewords: 34, ecPerBlock: 10, blocksGroup1: 1, dataGroup1: 34, blocksGroup2: 0, dataGroup2: 0, alignment: [6, 18] },
  { version: 3, totalDataCodewords: 55, ecPerBlock: 15, blocksGroup1: 1, dataGroup1: 55, blocksGroup2: 0, dataGroup2: 0, alignment: [6, 22] },
  { version: 4, totalDataCodewords: 80, ecPerBlock: 20, blocksGroup1: 1, dataGroup1: 80, blocksGroup2: 0, dataGroup2: 0, alignment: [6, 26] },
  { version: 5, totalDataCodewords: 108, ecPerBlock: 26, blocksGroup1: 1, dataGroup1: 108, blocksGroup2: 0, dataGroup2: 0, alignment: [6, 30] },
  { version: 6, totalDataCodewords: 136, ecPerBlock: 18, blocksGroup1: 2, dataGroup1: 68, blocksGroup2: 0, dataGroup2: 0, alignment: [6, 34] },
  { version: 7, totalDataCodewords: 156, ecPerBlock: 20, blocksGroup1: 2, dataGroup1: 78, blocksGroup2: 0, dataGroup2: 0, alignment: [6, 22, 38] },
  { version: 8, totalDataCodewords: 194, ecPerBlock: 24, blocksGroup1: 2, dataGroup1: 97, blocksGroup2: 0, dataGroup2: 0, alignment: [6, 24, 42] },
  { version: 9, totalDataCodewords: 232, ecPerBlock: 30, blocksGroup1: 2, dataGroup1: 116, blocksGroup2: 0, dataGroup2: 0, alignment: [6, 26, 46] },
  { version: 10, totalDataCodewords: 274, ecPerBlock: 18, blocksGroup1: 2, dataGroup1: 68, blocksGroup2: 2, dataGroup2: 69, alignment: [6, 28, 50] },
];

function encodeCodewords(bytes: Uint8Array, spec: VersionSpec): number[] {
  const bits: number[] = [];
  const push = (val: number, len: number) => {
    for (let i = len - 1; i >= 0; i--) bits.push((val >> i) & 1);
  };
  push(0b0100, 4);
  push(bytes.length, spec.version >= 10 ? 16 : 8);
  for (const b of bytes) push(b, 8);

  const capBits = spec.totalDataCodewords * 8;
  const termLen = Math.min(4, capBits - bits.length);
  for (let i = 0; i < termLen; i++) bits.push(0);
  while (bits.length % 8 !== 0) bits.push(0);

  const data: number[] = [];
  for (let i = 0; i < bits.length; i += 8) {
    let byte = 0;
    for (let b = 0; b < 8; b++) byte = (byte << 1) | bits[i + b];
    data.push(byte);
  }
  const pads = [0xec, 0x11];
  for (let k = 0; data.length < spec.totalDataCodewords; k++) data.push(pads[k % 2]);

  const dataBlocks: Uint8Array[] = [];
  const ecBlocks: Uint8Array[] = [];
  let offset = 0;
  for (let b = 0; b < spec.blocksGroup1; b++) {
    const blk = new Uint8Array(data.slice(offset, offset + spec.dataGroup1));
    offset += spec.dataGroup1;
    dataBlocks.push(blk);
    ecBlocks.push(rsEncode(blk, spec.ecPerBlock));
  }
  for (let b = 0; b < spec.blocksGroup2; b++) {
    const blk = new Uint8Array(data.slice(offset, offset + spec.dataGroup2));
    offset += spec.dataGroup2;
    dataBlocks.push(blk);
    ecBlocks.push(rsEncode(blk, spec.ecPerBlock));
  }

  const out: number[] = [];
  const maxDataLen = Math.max(spec.dataGroup1, spec.dataGroup2);
  for (let i = 0; i < maxDataLen; i++) {
    for (const blk of dataBlocks) if (i < blk.length) out.push(blk[i]);
  }
  for (let i = 0; i < spec.ecPerBlock; i++) {
    for (const ec of ecBlocks) out.push(ec[i]);
  }
  return out;
}

function drawFinder(grid: number[][], reserved: boolean[][], r0: number, c0: number) {
  const n = grid.length;
  for (let dr = -1; dr <= 7; dr++) {
    for (let dc = -1; dc <= 7; dc++) {
      const r = r0 + dr;
      const c = c0 + dc;
      if (r < 0 || r >= n || c < 0 || c >= n) continue;
      reserved[r][c] = true;
      const inBox = dr >= 0 && dr <= 6 && dc >= 0 && dc <= 6;
      const onBorder = dr === 0 || dr === 6 || dc === 0 || dc === 6;
      const inCore = dr >= 2 && dr <= 4 && dc >= 2 && dc <= 4;
      grid[r][c] = inBox && (onBorder || inCore) ? 1 : 0;
    }
  }
}

function drawAlignment(grid: number[][], reserved: boolean[][], cr: number, cc: number) {
  for (let dr = -2; dr <= 2; dr++) {
    for (let dc = -2; dc <= 2; dc++) {
      const r = cr + dr;
      const c = cc + dc;
      reserved[r][c] = true;
      grid[r][c] = Math.abs(dr) === 2 || Math.abs(dc) === 2 || (dr === 0 && dc === 0) ? 1 : 0;
    }
  }
}

function formatBits(mask: number): number {
  const data = (0b01 << 3) | (mask & 7);
  let rem = data << 10;
  const poly = 0b10100110111;
  for (let bit = 14; bit >= 10; bit--) {
    if ((rem >> bit) & 1) rem ^= poly << (bit - 10);
  }
  return ((data << 10) | rem) ^ 0b101010000010010;
}

function versionBits(version: number): number {
  let rem = version << 12;
  const poly = 0b1111100100101;
  for (let bit = 17; bit >= 12; bit--) {
    if ((rem >> bit) & 1) rem ^= poly << (bit - 12);
  }
  return (version << 12) | rem;
}

function maskFn(mask: number, r: number, c: number): boolean {
  switch (mask) {
    case 0: return (r + c) % 2 === 0;
    case 1: return r % 2 === 0;
    case 2: return c % 3 === 0;
    case 3: return (r + c) % 3 === 0;
    case 4: return (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0;
    case 5: return ((r * c) % 2) + ((r * c) % 3) === 0;
    case 6: return (((r * c) % 2) + ((r * c) % 3)) % 2 === 0;
    default: return (((r + c) % 2) + ((r * c) % 3)) % 2 === 0;
  }
}

function penalty(grid: number[][]): number {
  const n = grid.length;
  let score = 0;
  for (let r = 0; r < n; r++) {
    let rRun = 1;
    let cRun = 1;
    for (let k = 1; k < n; k++) {
      if (grid[r][k] === grid[r][k - 1]) rRun++;
      else { if (rRun >= 5) score += rRun - 2; rRun = 1; }
      if (grid[k][r] === grid[k - 1][r]) cRun++;
      else { if (cRun >= 5) score += cRun - 2; cRun = 1; }
    }
    if (rRun >= 5) score += rRun - 2;
    if (cRun >= 5) score += cRun - 2;
  }
  let dark = 0;
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      dark += grid[r][c];
      if (r + 1 < n && c + 1 < n) {
        const v = grid[r][c];
        if (grid[r][c + 1] === v && grid[r + 1][c] === v && grid[r + 1][c + 1] === v) score += 3;
      }
    }
  }
  const pct = (dark * 100) / (n * n);
  score += Math.floor(Math.abs(pct - 50) / 5) * 10;
  return score;
}

function applyFormatAndVersion(grid: number[][], version: number, mask: number) {
  const n = grid.length;
  const fmt = formatBits(mask);
  const topLeftCoords: [number, number][] = [
    [8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 7], [8, 8],
    [7, 8], [5, 8], [4, 8], [3, 8], [2, 8], [1, 8], [0, 8],
  ];
  for (let i = 0; i < 15; i++) {
    const bit = (fmt >> (14 - i)) & 1;
    const [r1, c1] = topLeftCoords[i];
    grid[r1][c1] = bit;
    if (i < 7) grid[n - 1 - i][8] = bit;
    else grid[8][n - 15 + i] = bit;
  }
  grid[n - 8][8] = 1;
  if (version >= 7) {
    const vb = versionBits(version);
    for (let i = 0; i < 18; i++) {
      const bit = (vb >> i) & 1;
      const a = Math.floor(i / 3);
      const b = (i % 3) + n - 11;
      grid[a][b] = bit;
      grid[b][a] = bit;
    }
  }
}

/** Deterministic boolean matrix (`true` = dark module) for any UTF-8 string up to ~271 bytes. */
export function encodeQrMatrix(text: string): boolean[][] {
  const bytes = new TextEncoder().encode(text);
  const spec = VERSIONS.find((v) => {
    const hdrBits = 4 + (v.version >= 10 ? 16 : 8);
    return Math.ceil((hdrBits + bytes.length * 8) / 8) <= v.totalDataCodewords;
  }) ?? VERSIONS[VERSIONS.length - 1];

  const clipped = bytes.slice(0, spec.totalDataCodewords - 3);
  const codewords = encodeCodewords(clipped, spec);
  const dataBits: number[] = [];
  for (const cw of codewords) {
    for (let b = 7; b >= 0; b--) dataBits.push((cw >> b) & 1);
  }

  const n = 4 * spec.version + 17;
  const base: number[][] = Array.from({ length: n }, () => Array(n).fill(0));
  const reserved: boolean[][] = Array.from({ length: n }, () => Array(n).fill(false));

  drawFinder(base, reserved, 0, 0);
  drawFinder(base, reserved, 0, n - 7);
  drawFinder(base, reserved, n - 7, 0);

  for (let i = 8; i < n - 8; i++) {
    reserved[6][i] = true;
    reserved[i][6] = true;
    base[6][i] = i % 2 === 0 ? 1 : 0;
    base[i][6] = i % 2 === 0 ? 1 : 0;
  }

  for (const r of spec.alignment) {
    for (const c of spec.alignment) {
      if ((r <= 8 && c <= 8) || (r <= 8 && c >= n - 9) || (r >= n - 9 && c <= 8)) continue;
      drawAlignment(base, reserved, r, c);
    }
  }

  for (let i = 0; i < 9; i++) {
    reserved[8][i] = true;
    reserved[i][8] = true;
  }
  for (let i = n - 8; i < n; i++) {
    reserved[8][i] = true;
    reserved[i][8] = true;
  }
  reserved[n - 8][8] = true;
  if (spec.version >= 7) {
    for (let a = 0; a < 6; a++) {
      for (let b = n - 11; b < n - 8; b++) {
        reserved[a][b] = true;
        reserved[b][a] = true;
      }
    }
  }

  let bitIdx = 0;
  let dir = -1;
  for (let right = n - 1; right > 0; right -= 2) {
    if (right === 6) right = 5;
    for (let step = 0; step < n; step++) {
      const r = dir === -1 ? n - 1 - step : step;
      for (const c of [right, right - 1]) {
        if (!reserved[r][c]) {
          base[r][c] = bitIdx < dataBits.length ? dataBits[bitIdx++] : 0;
        }
      }
    }
    dir = -dir;
  }

  let bestGrid = base;
  let bestScore = Infinity;
  for (let mask = 0; mask < 8; mask++) {
    const candidate = base.map((row, r) =>
      row.map((val, c) => (!reserved[r][c] && maskFn(mask, r, c) ? val ^ 1 : val)),
    );
    applyFormatAndVersion(candidate, spec.version, mask);
    const sc = penalty(candidate);
    if (sc < bestScore) {
      bestScore = sc;
      bestGrid = candidate;
    }
  }

  return bestGrid.map((row) => row.map((v) => v === 1));
}

export function qrSvgPath(matrix: boolean[][], quiet = 2): { viewBoxSize: number; d: string } {
  const n = matrix.length;
  const parts: string[] = [];
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      if (matrix[r][c]) {
        parts.push(`M${c + quiet},${r + quiet}h1v1h-1z`);
      }
    }
  }
  return { viewBoxSize: n + quiet * 2, d: parts.join("") };
}

export function QrCodeSvg({
  value,
  size = 84,
  label,
}: {
  value: string;
  size?: number;
  label?: string;
}) {
  const matrix = encodeQrMatrix(value);
  const { viewBoxSize, d } = qrSvgPath(matrix);
  return (
    <svg
      className="qr-code-svg"
      width={size}
      height={size}
      viewBox={`0 0 ${viewBoxSize} ${viewBoxSize}`}
      role="img"
      aria-label={label ?? `QR code for ${value}`}
      shapeRendering="crispEdges"
    >
      <rect width={viewBoxSize} height={viewBoxSize} fill="#ffffff" />
      <path d={d} fill="#111111" />
    </svg>
  );
}
