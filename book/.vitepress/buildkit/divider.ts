/**
 * 章/篇扉页与封面模板渲染：book/dividers/*.html 与 book/assets/cover.html
 * 模板语法为 Jinja2 子集（extends/block/if/default/变量），用 nunjucks
 * 以等价配置（trimBlocks/lstripBlocks/autoescape）渲染，模板源零改动。
 */
import {readFileSync} from 'node:fs'
import {join} from 'node:path'
import nunjucks from 'nunjucks'
import YAML from 'yaml'
import {BOOK_DIR} from './figures.ts'

const DIVIDERS_DIR = join(BOOK_DIR, 'dividers')

const env = new nunjucks.Environment(new nunjucks.FileSystemLoader(DIVIDERS_DIR), {
  autoescape: true,
  trimBlocks: true, // 对齐 Jinja2 trim_blocks
  lstripBlocks: true, // 对齐 Jinja2 lstrip_blocks
})

export type DividerContext = Record<string, string>

/** 渲染章/篇扉页模板，提取 body 内容内联进页面（去掉 <link> 与空行）。 */
export function renderDividerInline(context: DividerContext): string {
  const rendered = env.render(context.source_name, context)
  const m = /<body[^>]*>([\s\S]*?)<\/body>/.exec(rendered)
  if (!m) return ''
  let body = m[1]
  // 去掉模板自带的 divider.css 引用（web 端统一由 config 加载 /divider.css）
  body = body.replace(/<link[^>]*divider\.css[^>]*>/g, '')
  // 压缩空行，保持连续 HTML 块（避免 markdown-it 断裂；一次吃掉整段相邻空白行）
  body = body.replace(/\n(?:[ \t]*\n)+/g, '\n')
  return body
}

/** 篇扉页上下文（zh/en 同构，label 由调用方传入）。 */
export function partDividerContext(
  name: string,
  prefix: string | number,
  description: string,
  partIndex: number,
  lang: 'zh' | 'en',
): DividerContext {
  const themes = ['foundation', 'technology', 'application']
  const label = lang === 'zh' ? `第${prefix}篇` : `Part ${prefix}`
  return {
    source_name: `part-${String(partIndex).padStart(2, '0')}.html`,
    kind: 'part',
    theme: themes[(partIndex - 1) % themes.length],
    number: String(partIndex).padStart(2, '0'),
    label,
    english_label: `PART ${String(partIndex).padStart(2, '0')}`,
    title: name,
    title_main: name,
    title_sub: '',
    description,
  }
}

/** 章扉页上下文（zh 用全角"："分隔、en 用 ":" + title_sep）。 */
export function chapterDividerContext(
  ch: {id: number; title: string; description: string},
  partIndex: number,
  lang: 'zh' | 'en',
): DividerContext {
  const themes = ['foundation', 'technology', 'application']
  const sep = lang === 'zh' ? '：' : ':'
  const [titleMain, titleSub = ''] = ch.title.split(sep)
  return {
    source_name: `chapter-${String(ch.id).padStart(2, '0')}.html`,
    kind: 'chapter',
    theme: themes[(partIndex - 1) % themes.length],
    number: String(ch.id).padStart(2, '0'),
    label: lang === 'zh' ? `第${ch.id}章` : `Chapter ${ch.id}`,
    english_label: `CHAPTER ${String(ch.id).padStart(2, '0')}`,
    title: ch.title,
    title_main: titleMain,
    title_sub: lang === 'zh' ? titleSub : titleSub.trim(),
    ...(lang === 'en' ? {title_sep: ': '} : {}),
    description: ch.description,
  }
}

// ── CSS 作用域化 ───────────────────────────────────────────────────────────

const RULE_RE = /([^{}]+)\{([^{}]*)\}/g
const DIVIDER_DROP_SELECTORS = new Set(['*', 'html', 'body', 'html, body'])
const DIVIDER_VAR_SELECTORS = new Set([':root', '.dark'])

/** 把 divider.css 作用域化到 .divider-body 内，避免全局 html/body/h1 污染站点。 */
export function scopeDividerCss(css: string): string {
  css = css.replace(/\/\*[\s\S]*?\*\//g, '')
  const out: string[] = []
  for (const m of css.matchAll(RULE_RE)) {
    const selector = m[1].split(/\s+/).filter(Boolean).join(' ')
    const body = m[2]
    if (DIVIDER_DROP_SELECTORS.has(selector)) continue
    if (DIVIDER_VAR_SELECTORS.has(selector)) {
      out.push(`${selector} {${body}}`)
      continue
    }
    const scoped = selector.split(',').map((p) => p.trim()).filter(Boolean)
      .map((p) => `.divider-body ${p}`).join(', ')
    out.push(`${scoped} {${body}}`)
  }
  return out.join('\n')
}

/** 把封面 cover.html 的 <style> 作用域化到 .cover-body 内。 */
export function scopeCoverCss(css: string): string {
  css = css.replace(/\/\*[\s\S]*?\*\//g, '')
  // 移除 at-rule 块：@page（无嵌套）、@media print（一层嵌套）
  css = css.replace(/@page\s*\{[^{}]*\}/g, '')
  css = css.replace(/@media\s+print\s*\{[^{}]*\{[^{}]*\}[^{}]*\}/g, '')
  const out: string[] = []
  for (const m of css.matchAll(RULE_RE)) {
    const selector = m[1].split(/\s+/).filter(Boolean).join(' ')
    let body = m[2]
    if (selector === ':root' || selector === '.dark') {
      out.push(`${selector} {${body}}`)
      continue
    }
    if (selector === 'body') {
      // A4 210mm×297mm 按 96dpi（1mm≈3.7795px）折合 794×1123px，作缩放基准
      body = body.split('210mm').join('794px').split('297mm').join('1123px')
      out.push(`.cover-body {${body}}`)
      continue
    }
    if (selector === '*') {
      out.push(`.cover-body * {${body}}`)
      continue
    }
    const scoped = selector.split(',').map((p) => p.trim()).filter(Boolean)
      .map((p) => `.cover-body ${p}`).join(', ')
    out.push(`${scoped} {${body}}`)
  }
  return out.join('\n')
}

/** 渲染封面模板，返回 [作用域化 CSS, body HTML]。 */
export function renderCoverInline(lang: 'zh' | 'en' = 'zh'): [string, string] {
  const meta = YAML.parse(readFileSync(join(BOOK_DIR, 'config', 'book.yaml'), 'utf-8')) as Record<string, string>
  const nj = new nunjucks.Environment(null, {autoescape: true})
  const context = lang === 'en'
    ? {
        ...meta,
        language: 'en-US',
        title: 'From Industrial Software to AI Agents',
        subtitle: 'Building a multi-protocol, cloud-native, open-source industrial IoT platform ready for agentic evolution',
        author: 'Zhang Hongyuan',
        cover_tag: 'AI Native',
        cover_highlight_1: 'Five-layer architecture · Intelligence layer · IoT platform foundation',
        cover_highlight_2: 'LLMs · Agents · MCP · Tools · Skills · CLI · Intelligent operations',
        cover_highlight_3: 'IoT DC3 open-source project throughout the book',
        cover_highlight_4: '14 chapters · 200 figures · Engineering methodology',
        cover_author_role: 'Architect & IoT Expert',
        cover_brand: 'IoT DC3 · Open-source Industrial IoT',
        cover_brand_subtitle: 'Sense · Understand · Decide · Act',
      }
    : {
        ...meta,
        cover_tag: 'AI 原生',
        cover_highlight_1: '五层架构 · 智能层 · 物联网平台底座',
        cover_highlight_2: '大模型 · Agent · MCP · Tools · Skills · CLI · 智能运维',
        cover_highlight_3: 'IoT DC3 开源项目贯穿全书',
        cover_highlight_4: '14 章 · 200 张图表 · 工程方法论',
        cover_author_role: '架构师 & 物联网专家',
        cover_brand: '感知 · 理解 · 决策 · 执行',
        cover_brand_subtitle: 'Sense · Understand · Decide · Act',
      }
  const rendered = nj.renderString(readFileSync(join(BOOK_DIR, 'assets', 'cover.html'), 'utf-8'), context)

  const styleM = /<style[^>]*>([\s\S]*?)<\/style>/.exec(rendered)
  const css = styleM ? styleM[1] : ''
  const bodyM = /<body[^>]*>([\s\S]*?)<\/body>/.exec(rendered)
  let body = bodyM ? bodyM[1] : ''
  // logo.svg 相对路径 → 站点根
  body = body.split('src="logo.svg"').join('src="/logo.svg"')
  return [scopeCoverCss(css), body]
}
