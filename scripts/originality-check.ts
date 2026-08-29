#!/usr/bin/env bun
/**
 * 原创性自检：对比原文与改写稿，输出微信原创风险的代理指标。
 *
 * 指标：
 *  1. repeated_segments：改写稿中与原文连续相同 >= min-repeat 字的片段（默认 13 字，微信抄袭判定核心参考）
 *  2. lcs_length：最长公共子串长度
 *  3. ngram_overlap：n-gram（默认 8）重合率 = |改写稿 n-gram ∩ 原文 n-gram| / |改写稿 n-gram|
 *
 * 通过标准（全部满足，退出码 0）：
 *  - repeated_segments 为 0
 *  - lcs_length < min-repeat
 *  - ngram_overlap < 0.20
 *
 * 用法：
 *  bun originality-check.ts <原文.md> <改写稿.md> [--ngram 8] [--min-repeat 13] [--json]
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

interface Options {
  ngram: number;
  minRepeat: number;
  json: boolean;
}

function usage(): never {
  console.error(
    "用法: bun originality-check.ts <原文.md> <改写稿.md> [--ngram 8] [--min-repeat 13] [--json]"
  );
  process.exit(2);
}

function parseArgs(argv: string[]): { source: string; rewritten: string; opts: Options } {
  const opts: Options = { ngram: 8, minRepeat: 13, json: false };
  const positional: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]!;
    if (a === "--ngram") opts.ngram = parseInt(argv[++i] ?? "", 10);
    else if (a === "--min-repeat") opts.minRepeat = parseInt(argv[++i] ?? "", 10);
    else if (a === "--json") opts.json = true;
    else if (a === "--help" || a === "-h") usage();
    else positional.push(a);
  }
  if (positional.length < 2) usage();
  if (!Number.isFinite(opts.ngram) || opts.ngram < 2) usage();
  if (!Number.isFinite(opts.minRepeat) || opts.minRepeat < 2) usage();
  return { source: positional[0]!, rewritten: positional[1]!, opts };
}

/** 去除 YAML frontmatter */
function stripFrontmatter(text: string): string {
  if (!text.startsWith("---")) return text;
  const end = text.indexOf("\n---", 3);
  if (end === -1) return text;
  const nextLineStart = text.indexOf("\n", end + 4);
  return nextLineStart === -1 ? "" : text.slice(nextLineStart + 1);
}

/** 归一化：去空白、转小写（中文场景下标点保留） */
function normalize(text: string): string {
  return stripFrontmatter(text).replace(/\s+/g, "").toLowerCase();
}

function buildIndex(s: string, n: number): Map<string, number[]> {
  const index = new Map<string, number[]>();
  for (let i = 0; i + n <= s.length; i++) {
    const g = s.slice(i, i + n);
    const list = index.get(g);
    if (list) list.push(i);
    else index.set(g, [i]);
  }
  return index;
}

interface Segment {
  text: string;
  posInRewritten: number;
  length: number;
}

/** 扫描改写稿，找出所有与原文连续相同 >= minRepeat 的最大片段 */
function findRepeatedSegments(
  source: string,
  rewritten: string,
  n: number
): Segment[] {
  const index = buildIndex(source, n);
  const segments: Segment[] = [];
  let i = 0;
  while (i + n <= rewritten.length) {
    const g = rewritten.slice(i, i + n);
    const positions = index.get(g);
    if (positions && positions.length > 0) {
      // 在所有候选位置中取最长扩展
      let bestLen = 0;
      for (const pos of positions) {
        let len = 0;
        while (
          pos + len < source.length &&
          i + len < rewritten.length &&
          source[pos + len] === rewritten[i + len]
        ) {
          len++;
        }
        if (len > bestLen) bestLen = len;
      }
      if (bestLen >= n) {
        segments.push({
          text: rewritten.slice(i, i + bestLen),
          posInRewritten: i,
          length: bestLen,
        });
        i += bestLen; // 跳过已匹配区域，保证片段不重叠
        continue;
      }
    }
    i += 1;
  }
  return segments;
}

function ngramSet(s: string, n: number): Set<string> {
  const set = new Set<string>();
  for (let i = 0; i + n <= s.length; i++) set.add(s.slice(i, i + n));
  return set;
}

function ngramOverlap(source: string, rewritten: string, n: number): number {
  const a = ngramSet(source, n);
  const b = ngramSet(rewritten, n);
  if (b.size === 0) return 0;
  let common = 0;
  for (const g of b) if (a.has(g)) common++;
  return common / b.size;
}

// ---- 主流程 ----
const { source: sourcePath, rewritten: rewrittenPath, opts } = parseArgs(
  process.argv.slice(2)
);

let sourceRaw: string, rewrittenRaw: string;
try {
  sourceRaw = readFileSync(resolve(sourcePath), "utf-8");
  rewrittenRaw = readFileSync(resolve(rewrittenPath), "utf-8");
} catch (err) {
  console.error(`读取文件失败: ${(err as Error).message}`);
  process.exit(2);
}

const source = normalize(sourceRaw);
const rewritten = normalize(rewrittenRaw);

if (source.length === 0 || rewritten.length === 0) {
  console.error("归一化后文本为空，无法比对");
  process.exit(2);
}

const segments = findRepeatedSegments(source, rewritten, opts.minRepeat);
const lcs = segments.reduce((m, s) => Math.max(m, s.length), 0);
const overlap = ngramOverlap(source, rewritten, opts.ngram);

const pass =
  segments.length === 0 && lcs < opts.minRepeat && overlap < 0.2;

const report = {
  pass,
  metrics: {
    repeated_segments: segments.length,
    lcs_length: lcs,
    ngram_size: opts.ngram,
    ngram_overlap: Number(overlap.toFixed(4)),
    source_chars: source.length,
    rewritten_chars: rewritten.length,
  },
  thresholds: {
    repeated_segments: 0,
    lcs_length: opts.minRepeat,
    ngram_overlap: 0.2,
  },
  repeated_segments_detail: segments.slice(0, 20).map((s) => ({
    length: s.length,
    pos: s.posInRewritten,
    preview:
      s.text.length > 60 ? `${s.text.slice(0, 60)}…` : s.text,
  })),
};

if (opts.json) {
  console.log(JSON.stringify(report, null, 2));
} else {
  console.log(`原创性自检报告`);
  console.log(`  原文 / 改写稿字符数（归一化后）: ${source.length} / ${rewritten.length}`);
  console.log(`  连续重复片段（>= ${opts.minRepeat} 字）: ${segments.length} 个`);
  console.log(`  最长公共子串: ${lcs} 字`);
  console.log(`  ${opts.ngram}-gram 重合率: ${(overlap * 100).toFixed(2)}%`);
  if (segments.length > 0) {
    console.log(`  重复片段明细（前 ${Math.min(segments.length, 20)} 个）:`);
    for (const s of segments.slice(0, 20)) {
      console.log(`    [${s.length}字] ${s.text.length > 60 ? s.text.slice(0, 60) + "…" : s.text}`);
    }
  }
  console.log(pass ? `  结论: 通过 ✓` : `  结论: 未通过 ✗（需针对重复片段加强改写）`);
}

process.exit(pass ? 0 : 1);
