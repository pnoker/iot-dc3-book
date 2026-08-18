/**
 * 插图主题适配：把 SVG 源（book/figures/*.html）转为可响应明暗主题的内联 SVG。
 *
 * 策略：SVG 源保持纯色值，本模块在渲染/派生环节把 fill/stroke 色值替换为
 * CSS 变量 var(--fig-<hex>)，并生成 figures.css（:root 定义 light 原色、
 * .dark 定义暗色对应值）。颜色映射按 Tailwind 色板做「亮度阶反转」。
 *
 * 本文件是颜色映射的唯一权威来源（light → dark），供 buildkit 各模块复用。
 * （移植自 scripts/fig_theme.py，逻辑 1:1 对等，产物字节对拍验证。）
 */
import {readFileSync, readdirSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {join, dirname} from 'node:path'
import YAML from 'yaml'

const REPO_ROOT = fileURLToPath(new URL('../../../', import.meta.url))
export const BOOK_DIR = join(REPO_ROOT, 'book')
export const FIGURES_DIR = join(BOOK_DIR, 'figures')

/** 篇关键词 → (web slug, 篇扉页图名)，与旧 PART_SLUGS 对等 */
export const PART_SLUGS: Record<string, [string, string]> = {
  基础篇: ['foundations', 'part-01'],
  技术篇: ['technical', 'part-02'],
  应用篇: ['applications', 'part-03'],
}

// ── 图注册表 ────────────────────────────────────────────────────────────────

const _REGISTRY_CACHE = new Map<string, Record<string, unknown>>()

/** 加载一张图的注册表（spec + 双语 caption + 图内标注映射）；无注册表返回空对象。 */
export function loadFigureRegistry(figureId: string): Record<string, unknown> {
  const hit = _REGISTRY_CACHE.get(figureId)
  if (hit) return hit
  const chapter = figureId.split('-')[1]
  const path = join(FIGURES_DIR, `chapter-${chapter}`, `${figureId}.yaml`)
  let data: Record<string, unknown> = {}
  try {
    const loaded = YAML.parse(readFileSync(path, 'utf-8'))
    if (loaded && typeof loaded === 'object') data = loaded as Record<string, unknown>
  } catch {
    /* 无注册表 → 空 */
  }
  _REGISTRY_CACHE.set(figureId, data)
  return data
}

// ── 颜色映射（light → dark）────────────────────────────────────────────────
// 键为小写 hex，值为小写 hex。规则：
//  - 中性色（slate）按阶反转：50→900、900→100、200 边框→700 等
//  - 语义色浅底（50/100/200 卡片底）→ 对应深底（800/900）
//  - 语义色深字/描边（600~800）→ 对应亮档（300/400）
//  - 自定义近白底 → 中性深底 #1e293b（描边保留语义色）

export const COLOR_MAP: Record<string, string> = {
  // ── 中性色 slate/gray ──
  f8fafc: '0f172a', // slate-50 页面背景
  f1f5f9: '1e293b', // slate-100
  e2e8f0: '334155', // slate-200 边框
  cbd5e1: '475569', // slate-300 边框
  '94a3b8': '64748b', // slate-400
  '64748b': '94a3b8', // slate-500 弱文字
  '475569': '94a3b8', // slate-600 副文字
  '334155': 'cbd5e1', // slate-700 中文字
  '0f172a': 'f1f5f9', // slate-900 主文字
  '999': '64748b', // 自定义灰
  fff: '1e293b', // 英文 white（画布/白底卡片）
  ffffff: '1e293b', // 画布白 / 白底卡片

  // ── blue ──
  eff6ff: '1e3a8a', // blue-50 底 → blue-900
  dbeafe: '1e40af', // blue-100 → blue-800
  bfdbfe: '1e40af', // blue-200 → blue-800
  '93c5fd': '3b82f6', // blue-300 → blue-500
  '2563eb': '60a5fa', // blue-600 主色 → blue-400
  '1d4ed8': '60a5fa', // blue-700
  '1e40af': '93c5fd', // blue-800

  // ── teal ──
  f0fdfa: '134e4a', // teal-50 → teal-900
  ccfbf1: '115e59', // teal-100 → teal-800
  '99f6e4': '0f766e', // teal-200 → teal-700
  '5eead4': '0d9488', // teal-300 → teal-600
  '0f766e': '2dd4bf', // teal-700 主色 → teal-400

  // ── emerald ──
  ecfdf5: '064e3b', // emerald-50 → emerald-900
  d1fae5: '065f46', // emerald-100 → emerald-800
  a7f3d0: '047857', // emerald-200 → emerald-700
  '059669': '34d399', // emerald-600
  '047857': '34d399', // emerald-700
  '065f46': '6ee7b7', // emerald-800
  '10b981': '34d399', // emerald-500

  // ── green ──
  f0fdf4: '14532d', // green-50 → green-900
  dcfce7: '166534', // green-100 → green-800
  bbf7d0: '15803d', // green-200 → green-700
  '86efac': '16a34a', // green-300 → green-600
  '22c55e': '4ade80', // green-500
  '16a34a': '4ade80', // green-600 主色
  '15803d': '4ade80', // green-700
  '166534': '86efac', // green-800

  // ── orange ──
  fff7ed: '7c2d12', // orange-50 → orange-900
  ffedd5: '9a3412', // orange-100 → orange-800
  fed7aa: 'c2410c', // orange-200 → orange-700
  fdba74: 'ea580c', // orange-300 → orange-600
  f97316: 'fb923c', // orange-500 主色 → orange-400
  ea580c: 'fb923c', // orange-600
  c2410c: 'fb923c', // orange-700
  '9a3412': 'fdba74', // orange-800

  // ── amber ──
  fffbeb: '78350f', // amber-50 → amber-900
  fef3c7: '92400e', // amber-100 → amber-800
  fde68a: 'b45309', // amber-200 → amber-700
  fcd34d: 'd97706', // amber-300 → amber-600
  f59e0b: 'fbbf24', // amber-500
  d97706: 'fbbf24', // amber-600 警示
  b45309: 'fcd34d', // amber-700
  '92400e': 'fcd34d', // amber-800

  // ── red ──
  fef2f2: '450a0a', // red-50 → red-950
  fee2e2: '7f1d1d', // red-100 → red-900
  dc2626: 'f87171', // red-600 主色 → red-400
  b91c1c: 'fca5a5', // red-700
  '991b1b': 'fca5a5', // red-800
  '7f1d1d': 'fca5a5', // red-900

  // ── violet ──
  f5f3ff: '2e1065', // violet-50 → violet-950
  ede9fe: '4c1d95', // violet-100 → violet-900
  ddd6fe: '5b21b6', // violet-200 → violet-800
  c4b5fd: '6d28d9', // violet-300 → violet-700
  a78bfa: '7c3aed', // violet-400 → violet-600
  '7c3aed': 'a78bfa', // violet-600 主色 → violet-400
  '6d28d9': 'c4b5fd', // violet-700

  // ── cyan ──
  ecfeff: '164e63', // cyan-50 → cyan-900
  '0891b2': '22d3ee', // cyan-600

  // ── 自定义近白底（描边保留语义色，底统一中性深灰）──
  f0f8ff: '1e293b', // aliceblue（蓝调白）
  f0fbf5: '1e293b',
  f3faf6: '1e293b',
  f5fcf9: '1e293b',
  f7faff: '1e293b',
  f8fcfb: '1e293b',
  faf5ff: '1e293b',
  faf8ff: '1e293b',
  fbfdff: '1e293b',
  fefce8: '1e293b',
  fff7e6: '1e293b',
  fff8dc: '1e293b',
  fff8e7: '1e293b',
  fff9f2: '1e293b',
  fffbf4: '1e293b',

  // ── rgba() 专用：半透明背景分区 / 填充的语义色（原浅色 → 深色调）──
  '87cefa': '1e3a8a', // skyblue 室外域浅蓝 → blue-900
  ffff00: '78350f', // 过渡区纯黄 → amber-900
  c8c8c8: '475569', // 室内域中性浅灰 → slate-600

  // ── 补充：重绘批次引入、原表遗漏的色值（缺失会让 var(--fig-*) 未定义 → 局部暗色）──
  '0ea5e9': '38bdf8', // sky-500 主色 → sky-400
  '60a5fa': '93c5fd', // blue-400 → blue-300
  '6ee7b7': '34d399', // emerald-300 → emerald-400
  a16207: 'fcd34d', // amber-700 警示字（部分具备）→ amber-300
  ca8a04: 'fbbf24', // amber-600 警示 → amber-400
  fef9c3: '92400e', // amber-100 警示底（部分具备）→ amber-800
  fecaca: '7f1d1d', // red-200 浅红 → red-900
  e0f2fe: '0c4a6e', // sky-100 浅蓝底 → sky-900
  bbd4ff: '1e40af', // blue-200 渐变浅蓝 → blue-800
  c6daff: '1e40af', // blue-100/200 渐变浅蓝 → blue-800
  d0e0ff: '1e40af', // blue-100 渐变浅蓝 → blue-800
  dae7ff: '1e40af', // blue-100 渐变浅蓝 → blue-800
  e4edff: '1e3a8a', // blue-50/100 渐变浅蓝 → blue-900
  edf3ff: '1e3a8a', // blue-50 渐变浅蓝 → blue-900
  f5f8ff: '1e293b', // 近白蓝底 → 中性深底
}

// 色值 → CSS 变量名。var(--fig-<hex>)；覆盖 fill/stroke/stop-color 属性
const COLOR_RE = /((?:fill|stroke|stop-color))="(#[0-9a-fA-F]{3,8})"/g
// rgba(r,g,b,a) 半透明色（背景分区/填充）：颜色部分变量化，透明度保留
const RGBA_RE = /(fill|stroke)="rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([0-9.]+))?\s*\)"/g

function hexToRgb(hexv: string): [number, number, number] {
  return [
    parseInt(hexv.slice(0, 2), 16),
    parseInt(hexv.slice(2, 4), 16),
    parseInt(hexv.slice(4, 6), 16),
  ]
}

/**
 * 把一段 SVG（含内联）中的色值替换为 CSS 变量（含 rgba/stop-color）。
 * 并压缩空行：markdown-it 的 HTML 块规则遇空行会中断 HTML 块，
 * 导致 Vue 编译器看到断裂标签，因此内联进 md 前必须去掉空行。
 */
export function svgToTheme(svgMarkup: string): string {
  let out = svgMarkup.replace(COLOR_RE, (_m, attr: string, hexv: string) => {
    return `${attr}="var(--fig-${hexv.replace(/^#/, '').toLowerCase()})"`
  })
  out = out.replace(
    RGBA_RE,
    (m: string, attr: string, r: string, g: string, b: string, a?: string) => {
      const hexv = [r, g, b]
        .map((v) => Number(v).toString(16).padStart(2, '0'))
        .join('')
      if (hexv in COLOR_MAP) return `${attr}="rgba(var(--fig-rgb-${hexv}), ${a ?? '1'})"`
      return m
    },
  )
  // 英文色名 white / black 等
  out = out.replace(/(fill|stroke)="white"/gi, '$1="var(--fig-ffffff)"')
  // 压缩空行（保留单换行，标签间不断裂）
  out = out.replace(/\n[ \t]*\n+/g, '\n')
  return out
}

/** 从 figure HTML 源提取 data-figure-root 容器内的 SVG 内容（四形态栈匹配）。 */
export function extractInlineSvg(html: string): string {
  const rootM = /<([a-zA-Z]+)([^>]*?\sdata-figure-root[^>]*)>/s.exec(html)
  if (!rootM) return ''
  const tag = rootM[1]
  const start = rootM.index + rootM[0].length

  const openPat = new RegExp(`<${tag}(?:\\s[^>]*)?/?>`, 'i')
  const closePat = new RegExp(`</${tag}\\s*>`, 'i')
  let depth = 1
  let pos = start
  while (depth > 0) {
    const om = openPat.exec(html.slice(pos))
    const cm = closePat.exec(html.slice(pos))
    if (!cm) return '' // 未闭合，异常源
    if (om && om.index < cm.index) {
      // 跳过自闭合 <tag/>
      if (!om[0].endsWith('/>')) depth += 1
      pos += om.index + om[0].length
    } else {
      depth -= 1
      pos += cm.index + cm[0].length
    }
  }

  const container = html.slice(rootM.index, pos)
  // 若容器本身是 svg，直接返回；否则返回其 innerHTML（剥离 main/div 包装）
  if (tag.toLowerCase() === 'svg') return container
  let inner = container.replace(/^<[a-zA-Z]+[^>]*>/, '')
  inner = inner.replace(/<\/[a-zA-Z]+>$/, '')
  return inner
}

// SVG 内 <style>：客户端组件模板会拒绝 <style>，且其中颜色硬编码暗色不生效。
// 须提取出来、作用域化到 .fig-<id> 类。
const STYLE_RE = /<style\b[^>]*>([\s\S]*?)<\/style>/gi
const STYLE_COLOR_RE = /(fill|stroke)\s*:\s*(#[0-9a-fA-F]{3,8})\b/gi

/** 提取 SVG 内 <style>，颜色变量化 + 作用域化到 .fig-<id>。返回 [移除后 svg, 作用域化 CSS]。 */
export function extractAndScopeStyle(svg: string, figureId: string): [string, string] {
  const scopedRules: string[] = []
  const svgOut = svg.replace(STYLE_RE, (_m, cssText: string) => {
    // 颜色变量化：fill: #xxx → fill: var(--fig-xxx)
    const themed = cssText.replace(
      STYLE_COLOR_RE,
      (_cm, prop: string, hexv: string) => `${prop}: var(--fig-${hexv.replace(/^#/, '').toLowerCase()})`,
    )
    for (const rule of themed.split('}')) {
      if (!rule.includes('{')) continue
      const idx = rule.indexOf('{')
      const sel = rule.slice(0, idx)
      const body = rule.slice(idx + 1)
      const sels = sel.split(',').map((s) => s.trim()).filter(Boolean)
      if (!sels.length) continue
      scopedRules.push(`${sels.map((s) => `.${figureId} ${s}`).join(', ')} {${body}}`)
    }
    return ''
  })
  return [svgOut, scopedRules.join('\n')]
}

/** 扫描所有图，返回 rgba() 中用到、且已在 COLOR_MAP 的颜色 hex 集合。 */
export function collectRgbaHexes(htmls: Iterable<[string, string]>): Set<string> {
  const hexes = new Set<string>()
  for (const [, html] of htmls) {
    const inline = extractInlineSvg(html)
    for (const m of inline.matchAll(RGBA_RE)) {
      const hexv = [m[2], m[3], m[4]]
        .map((v) => Number(v).toString(16).padStart(2, '0'))
        .join('')
      if (hexv in COLOR_MAP) hexes.add(hexv)
    }
  }
  return hexes
}

/** 生成 figures.css：:root 定义原色、.dark 定义暗色对应值（含 rgba 三元组变量）。 */
export function genFiguresCss(rgbHexes: Set<string> = new Set()): string {
  const entries = Object.entries(COLOR_MAP).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
  const lines = [
    '/* 自动生成，请勿手改 —— 由 book/.vitepress/buildkit/figures.ts 产出 */',
    ':root {',
  ]
  for (const [hexv] of entries) lines.push(`  --fig-${hexv}: #${hexv};`)
  for (const hexv of [...rgbHexes].sort()) {
    const [r, g, b] = hexToRgb(hexv)
    lines.push(`  --fig-rgb-${hexv}: ${r}, ${g}, ${b};`)
  }
  lines.push('}', '')
  lines.push('.dark {')
  for (const [hexv, dark] of entries) lines.push(`  --fig-${hexv}: #${dark};`)
  for (const hexv of [...rgbHexes].sort()) {
    const [dr, dg, db] = hexToRgb(COLOR_MAP[hexv])
    lines.push(`  --fig-rgb-${hexv}: ${dr}, ${dg}, ${db};`)
  }
  lines.push('}', '')
  return lines.join('\n')
}

// ── 插图多语言 ─────────────────────────────────────────────────────────────

const CJK_RE = /[一-鿿]/
const SVG_TEXT_RE = />([^<>]*[一-鿿][^<>]*)</g

export function hasCjk(s: string): boolean {
  return CJK_RE.test(s)
}

/** 从注册表读取 {figure_id}.yaml 的 labels.{lang} 文本映射；缺失返回空。 */
export function loadFigureI18n(figureId: string, lang: string): Record<string, string> {
  const labels = (loadFigureRegistry(figureId).labels ?? {}) as Record<string, unknown>
  const data = labels[lang]
  if (!data || typeof data !== 'object') return {}
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(data as Record<string, unknown>)) out[k] = String(v)
  return out
}

/** 按映射替换 SVG 文本（长串优先，避免子串先替换造成拼接残留）。 */
export function applyFigureI18n(svg: string, figureId: string, lang: string): string {
  const pairs = loadFigureI18n(figureId, lang)
  for (const zh of Object.keys(pairs).sort((a, b) => b.length - a.length)) {
    if (pairs[zh]) svg = svg.split(zh).join(pairs[zh])
  }
  return svg
}

/** 抽取一张图 SVG 内全部含 CJK 的文本（去重、保持出现顺序），供生成翻译桩。 */
export function extractFigureTexts(html: string): string[] {
  const [inline] = extractAndScopeStyle(extractInlineSvg(html), '')
  const seen = new Set<string>()
  const texts: string[] = []
  for (const m of inline.matchAll(SVG_TEXT_RE)) {
    const t = m[1].trim()
    if (t && !seen.has(t)) {
      seen.add(t)
      texts.push(t)
    }
  }
  return texts
}

/**
 * 按 figure_id 定位并返回 theme 化的内联 SVG；找不到返回 null。
 * lang !== "zh" 时应用注册表的文本映射（无映射则回落中文标注）。
 */
export function loadFigureSvg(figureId: string, lang = 'zh'): string | null {
  const chapter = figureId.split('-')[1] // fig-03-01 → 03
  const srcFile = join(FIGURES_DIR, `chapter-${chapter}`, `${figureId}.html`)
  let html: string
  try {
    html = readFileSync(srcFile, 'utf-8')
  } catch {
    return null
  }
  let inline = extractInlineSvg(html)
  // 剥离 HTML 注释（源码分节注释不参与渲染，也避免多语言审计误报）
  inline = inline.replace(/<!--[\s\S]*?-->/g, '')
  // 提取并作用域化 <style>（移除标签，规则交给 figures.css）
  const [styled, scopedCss] = extractAndScopeStyle(inline, figureId)
  if (scopedCss) figureScopedStyles.set(figureId, scopedCss)
  inline = styled
  // 给最外层 svg 根加类，供作用域化规则匹配
  inline = inline.replace(/<svg\b/, `<svg class="${figureId}"`)
  inline = svgToTheme(inline)
  if (lang !== 'zh') inline = applyFigureI18n(inline, figureId, lang)
  // 唯一化 title/desc id，避免同页多图内联时 id 冲突（正文多图 + 图库 200+ 图）
  inline = inline.split('id="title"').join(`id="${figureId}-title"`)
  inline = inline.split('id="desc"').join(`id="${figureId}-desc"`)
  inline = inline
    .split('aria-labelledby="title desc"')
    .join(`aria-labelledby="${figureId}-title ${figureId}-desc"`)
  return inline
}

/** 渲染期收集的 SVG 内 <style> 作用域化规则（assets 生成 figures.css 时合并） */
export const figureScopedStyles = new Map<string, string>()

/** 扫描所有图源 html，返回 {figure_id: html}（按 id 排序）。 */
export function readAllFigureHtmls(): Map<string, string> {
  const out = new Map<string, string>()
  for (const id of listFigureIds()) {
    const chapter = id.split('-')[1]
    out.set(id, readFileSync(join(FIGURES_DIR, `chapter-${chapter}`, `${id}.html`), 'utf-8'))
  }
  return out
}

let _figureIds: string[] | null = null

/** 列出全部图 id（fig-XX-YY，按章目录与文件名排序）。 */
export function listFigureIds(): string[] {
  if (_figureIds) return _figureIds
  const ids: string[] = []
  for (const dir of readdirSync(FIGURES_DIR, {withFileTypes: true})
    .filter((d) => d.isDirectory() && /^chapter-\d+$/.test(d.name))
    .map((d) => d.name)
    .sort()) {
    for (const f of readdirSync(join(FIGURES_DIR, dir)).filter((f) => f.endsWith('.html')).sort()) {
      ids.push(f.replace(/\.html$/, ''))
    }
  }
  _figureIds = ids
  return ids
}

/** 色值覆盖审计：返回 COLOR_MAP 未覆盖的色值 → 使用该色的图 id 集合。 */
export function auditColorCoverage(htmls: Map<string, string>): Record<string, string[]> {
  const missing: Record<string, string[]> = {}
  for (const [id, html] of htmls) {
    const inline = extractInlineSvg(html)
    for (const m of inline.matchAll(/(?:fill|stroke|stop-color)="(#[0-9a-fA-F]{3,8})"/g)) {
      const hexv = m[1].replace(/^#/, '').toLowerCase()
      if (!(hexv in COLOR_MAP)) (missing[hexv] ??= []).push(id)
    }
    for (const m of inline.matchAll(
      /(?:fill|stroke)="rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/g,
    )) {
      const hexv = [m[1], m[2], m[3]]
        .map((v) => Number(v).toString(16).padStart(2, '0'))
        .join('')
      if (!(hexv in COLOR_MAP)) (missing[`rgba ${hexv}`] ??= []).push(id)
    }
  }
  return missing
}

// ── 工具：与 Python json.dumps(obj, ensure_ascii=False) 字节对齐的序列化 ──

export function jsonDumpsPy(value: unknown): string {
  if (value === null || typeof value === 'boolean' || typeof value === 'number') {
    return JSON.stringify(value)
  }
  if (typeof value === 'string') return JSON.stringify(value)
  if (Array.isArray(value)) {
    return '[' + value.map(jsonDumpsPy).join(', ') + ']'
  }
  const entries = Object.entries(value as Record<string, unknown>)
  return '{' + entries.map(([k, v]) => `${JSON.stringify(k)}: ${jsonDumpsPy(v)}`).join(', ') + '}'
}
