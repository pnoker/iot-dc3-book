/**
 * markdown-it 插件：手稿即终稿的渲染期变换。
 *
 * 在 markdown 渲染最前（@mdit-vue/frontmatter 之前）按页面类型改写 state.src：
 *   - 节页（manuscript/{lang}/chapter-XX/X.Y.md）：标题升级（H2→H1、H3+ 降一级）、
 *     byline、上/下节导航、@[fig] → 主题化双语内联 SVG；
 *   - 章首页/篇页/目录页（pages/{lang} stub）：渲染期注入扉页与结构清单；
 *   - 卷首/附录：frontmatter 标签注入 + 锚点解析。
 * 页面语言由重写后路径（或源路径兜底）判定，SSG 构建期即产出最终静态 HTML。
 */
import {readFileSync, existsSync} from 'node:fs'
import {join} from 'node:path'
import type MarkdownIt from 'markdown-it'
import {BOOK_DIR, loadFigureSvg, loadFigureRegistry} from './figures.ts'
import {
  getSite,
  rewrite as rewritePath,
  gitLastmod,
  prefaceTable,
  figureTitleEn,
  type Lang,
  type Part,
  type Chapter,
} from './site.ts'
import {renderDividerInline, partDividerContext, chapterDividerContext} from './divider.ts'

// ── 与旧产物对等的常量与工具 ───────────────────────────────────────────────

const BYLINE = (
  '<div class="book-byline">'
  + '作者：张红元 · © 2016–2026 · 保留所有权利 · '
  + '<a href="/copyright">版权与许可</a>'
  + '</div>'
)
const BYLINE_EN = (
  '<div class="book-byline">'
  + 'Author: Zhang Hongyuan · © 2016–2026 · All Rights Reserved · '
  + '<a href="/en/copyright">Copyright &amp; License</a>'
  + '</div>'
)

function fmStr(kv: Record<string, string>): string {
  const lines = ['---']
  for (const [k, v] of Object.entries(kv)) lines.push(`${k}: ${JSON.stringify(v)}`)
  lines.push('---')
  return lines.join('\n') + '\n\n'
}

function oneline(s: string): string {
  return (s || '').replace(/\s+/g, ' ').trim()
}

function fixCaption(alt: string): string {
  return alt.replace(/图(\d)/g, '图 $1')
}

/** 从正文首段提取 description（跳过标题/代码/列表/表格/HTML）。 */
export function extractDescription(body: string, maxLen = 130): string {
  const text = body.replace(/^#.*$/gm, '')
  for (const line of text.split('\n')) {
    const s = line.trim()
    if (!s || /^(```|>|[-*|<!])/.test(s)) continue
    const desc = s.replace(/[`*]/g, '').trim()
    if (desc.length >= 20) return desc.slice(0, maxLen) + (desc.length > maxLen ? '…' : '')
  }
  return ''
}

/** 标题升级：首个 H2 → H1，H3~H6 整体降一级（围栏代码块内不动）。 */
function shiftHeadings(md: string): string {
  // 兼容 CRLF：_intro.md 等 readFileSync 直读路径不经 transformPage 的归一化
  const lines = md.replace(/\r\n?/g, '\n').split('\n')
  let inCode = false
  let h1Done = false
  return lines
    .map((line) => {
      if (/^\s*```/.test(line)) {
        inCode = !inCode
        return line
      }
      if (inCode) return line
      if (!h1Done) {
        const m = /^##\s+(.+)$/.exec(line)
        if (m) {
          h1Done = true
          return `# ${m[1]}`
        }
      }
      return line.replace(/^(#{3,6})\s+(.*)$/, (_m, hashes: string, rest: string) => {
        return '#'.repeat(hashes.length - 1) + ' ' + rest
      })
    })
    .join('\n')
}

function genSectionNav(prev?: [string, string], next?: [string, string]): string {
  const parts: string[] = []
  if (prev) parts.push(`<a class="nav-prev" href="${prev[1]}">← ${prev[0]}</a>`)
  if (next) parts.push(`<a class="nav-next" href="${next[1]}">${next[0]} →</a>`)
  if (!parts.length) return ''
  return '\n<nav class="section-nav">\n  ' + parts.join('\n  ') + '\n</nav>\n'
}

/** 把章描述拓展成一段简洁的概览总结（连贯成段，不列节标题）。 */
export function genChapterOverview(desc: string, sections: {stem: string; title: string}[]): string {
  const topics: string[] = []
  for (const s of sections) {
    if (!s.stem) continue
    let topic = s.title.replace(/^\d+\.\d+\s*/, '').trim()
    topic = topic.split(/[：——]/)[0].trim()
    if (topic) topics.push(topic)
  }
  const base = desc.replace(/[。！？；\n]+$/, '').trimEnd()
  if (!topics.length) return base
  let chain: string
  if (topics.length === 1) {
    chain = `聚焦${topics[0]}`
  } else if (topics.length === 2) {
    chain = `先讲${topics[0]}，最后落在${topics[1]}`
  } else if (topics.length <= 5) {
    const mid = topics.slice(1, -1).join('、')
    chain = `先讲${topics[0]}，再到${mid}，最后落在${topics[topics.length - 1]}`
  } else {
    const mid = topics.slice(1, 4).join('、') + `等${topics.length - 1}个主题`
    chain = `先讲${topics[0]}，再到${mid}，最后落在${topics[topics.length - 1]}`
  }
  return `${base}。本章${chain}。`
}

// ── @[fig-XX-YY] → 内联 SVG ────────────────────────────────────────────────

const ANCHOR_LINE_RE = /^@\[(fig-\d{2}-\d{2})\][ \t]*$/gm

/** 插图锚点 → <figure>：内联 theme 化 SVG（明暗主题 + 注册表 labels 文本覆盖）。 */
function figureHtml(figId: string, lang: Lang): string {
  const inline = loadFigureSvg(figId, lang)
  const reg = loadFigureRegistry(figId)
  let title = String(reg.title ?? figId)
  if (lang !== 'zh') title = figureTitleEn(figId, reg) ?? title
  const cap = `  <figcaption>${fixCaption(title)}</figcaption>\n`
  if (inline) {
    return (
      `<figure class="fig fig-svg" id="${figId}">\n`
      + `  <div class="fig-svg-body">${inline}</div>\n`
      + cap
      + '</figure>'
    )
  }
  console.warn(`⚠️  插图缺少 SVG 源：${figId}（仅输出图注）`)
  return `<figure class="fig" id="${figId}">\n${cap}</figure>`
}

function resolveAnchors(md: string, lang: Lang): string {
  return md.replace(ANCHOR_LINE_RE, (_m, figId: string) => figureHtml(figId, lang))
}

function stripFm(md: string): string {
  return md.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, '')
}

// ── 页面类型判定（重写后路径优先，源路径兜底）──────────────────────────────

interface PageInfo {
  kind: 'section' | 'chapter' | 'part' | 'contents' | 'preface' | 'appendix' | 'plain'
  lang: Lang
  /** 输出路径（srcDir 相对） */
  out: string
}

const SLUGS = ['foundations', 'technical', 'applications']

function classify(rel: string): PageInfo | null {
  if (rel === 'index.md' || rel === 'figures.md' || rel === 'copyright.md'
    || rel === 'en/index.md' || rel === 'en/figures.md' || rel === 'en/copyright.md') {
    return null // 手写站页，不处理
  }
  const lang: Lang = rel === 'en/index.md' || rel.startsWith('en/') ? 'en' : 'zh'
  const body = lang === 'en' ? rel.slice(3) : rel

  // 重写后路径形态
  for (const slug of SLUGS) {
    let m = new RegExp(`^${slug}/chapter-(\\d+)/(\\d+)-(\\d+)\\.md$`).exec(body)
    if (m) return {kind: 'section', lang, out: rel}
    m = new RegExp(`^${slug}/chapter-(\\d+)/index\\.md$`).exec(body)
    if (m) return {kind: 'chapter', lang, out: rel}
    m = new RegExp(`^${slug}/index\\.md$`).exec(body)
    if (m) return {kind: 'part', lang, out: rel}
  }
  if (body === 'preface/contents.md') return {kind: 'contents', lang, out: rel}
  if (/^preface\/[\w-]+\.md$/.test(body)) return {kind: 'preface', lang, out: rel}
  if (body === 'appendix/index.md') return {kind: 'appendix', lang, out: rel}

  // 源路径形态兜底（env 给出未重写路径时）
  const src = lang === 'en' ? rel : rel
  if (/^manuscript\/zh\//.test(src) || /^manuscript\/en\//.test(src)
    || /^pages\/(zh|en)\//.test(src)) {
    const mapped = rewritePath(src)
    if (mapped && mapped !== src) return classify(mapped)
  }
  return null
}

// ── 各页面类型的渲染 ───────────────────────────────────────────────────────

function findChapter(lang: Lang, cid: number): {part: Part; ch: Chapter} | null {
  for (const part of getSite()[lang]) {
    const ch = part.chapters.find((c) => c.id === cid)
    if (ch) return {part, ch}
  }
  return null
}

function renderSection(info: PageInfo, src: string): string {
  const site = getSite()
  const navMap = info.lang === 'en' ? site.navEn : site.navZh
  const nav = navMap.get(info.out)
  // 标题升级后 body 自带 "# title"；对齐旧结构 fm + "# title\n" + BYLINE + "" + body
  const bodyFull = shiftHeadings(stripFm(src)).trim()
  const nl = bodyFull.indexOf('\n')
  const title = nl >= 0 ? bodyFull.slice(0, nl).replace(/^#\s+/, '') : bodyFull.replace(/^#\s+/, '')
  const body = nl >= 0 ? bodyFull.slice(nl + 1).trim() : ''
  const out = [
    // 旧管线锚点先解析为 <figure>（首段提取时被跳过）；此处等价地先剥锚点行
    fmStr({title, description: extractDescription(body.replace(ANCHOR_LINE_RE, ''))}),
    `# ${title}\n`,
    info.lang === 'en' ? BYLINE_EN : BYLINE,
    '',
    body,
  ]
  const navHtml = genSectionNav(nav?.prev, nav?.next)
  if (navHtml) {
    out.push('')
    out.push(navHtml)
  }
  return out.join('\n') + '\n'
}

function renderChapter(info: PageInfo): string {
  const cidM = /chapter-(\d+)/.exec(info.out)!
  const cid = Number(cidM[1])
  const hit = findChapter(info.lang, cid)
  if (!hit) return ''
  const {ch} = hit
  const dividerCtx = chapterDividerContext(ch, ch.partIndex, info.lang)
  let dividerHtml = renderDividerInline(dividerCtx)
  if (info.lang === 'zh') {
    const overview = genChapterOverview(ch.description, ch.sections)
    dividerHtml = dividerHtml.replace(
      /<p class="overview">[\s\S]*?<\/p>/,
      `<p class="overview">${overview}</p>`,
    )
  }
  const introPath = join(
    BOOK_DIR, 'manuscript', info.lang, `chapter-${String(cid).padStart(2, '0')}`, '_intro.md',
  )
  let intro = ''
  if (existsSync(introPath)) {
    intro = shiftHeadings(stripFm(readFileSync(introPath, 'utf-8'))).trim()
  }
  const title = info.lang === 'zh' ? `第 ${cid} 章　${ch.title}` : `Chapter ${cid}. ${ch.title}`
  const parts = [fmStr({title, description: oneline(ch.description)})]
  if (dividerHtml) {
    parts.push(
      '<figure class="chapter-divider">\n'
      + `  <div class="divider-body">${dividerHtml}</div>\n`
      + '</figure>\n',
    )
  }
  if (intro) {
    parts.push(intro)
    parts.push('')
  }
  return parts.join('\n') + '\n'
}

function renderPart(info: PageInfo): string {
  const site = getSite()
  const slug = (info.lang === 'en' ? info.out.slice(3) : info.out).split('/')[0]
  const part = site[info.lang].find((p) => p.slug === slug)
  if (!part) return ''
  const dividerHtml = renderDividerInline(
    partDividerContext(part.name, part.prefix || part.partIndex, part.description, part.partIndex, info.lang),
  )
  const desc = oneline(part.description)
  const out = [fmStr({title: part.name, description: desc})]
  if (dividerHtml) {
    out.push(
      '<figure class="part-divider">\n'
      + `  <div class="divider-body">${dividerHtml}</div>\n`
      + '</figure>\n',
    )
  }
  out.push(`# ${part.name}\n`)
  out.push(`\n> ${desc}\n`)
  if (info.lang === 'zh') {
    out.push('\n## 本章包含\n')
    for (const ch of part.chapters) {
      out.push(
        `- [第 ${ch.id} 章　${ch.title}](/${part.slug}/chapter-${ch.id}/)`
        + ` — ${oneline(ch.description)}`,
      )
    }
  } else {
    out.push('\n## Chapters in this part\n')
    for (const ch of part.chapters) {
      const lineTitle = `Chapter ${ch.id}. ${ch.title}`
      const cdesc = oneline(ch.description)
      if (ch.sections.length) {
        out.push(`- [${lineTitle}](/en/${part.slug}/chapter-${ch.id}/) — ${cdesc}`)
      } else {
        out.push(
          `- ${lineTitle} — ${cdesc}`
          + ` *(not yet translated — [read in Chinese](/${part.slug}/chapter-${ch.id}/))*`,
        )
      }
    }
  }
  return out.join('\n') + '\n'
}

function renderContents(info: PageInfo): string {
  const site = getSite()
  if (info.lang === 'zh') {
    const out = [fmStr({title: '目录', description: '《从工业软件到 AI 智能体》全书目录'})]
    out.push('# 目录\n')
    for (const part of site.zh) {
      out.push(`\n## ${part.name}\n`)
      out.push(`\n> ${oneline(part.description)}\n`)
      out.push('')
      for (const ch of part.chapters) {
        out.push(`- [第 ${ch.id} 章　${ch.title}](/${part.slug}/chapter-${ch.id}/)`)
      }
    }
    return out.join('\n') + '\n'
  }
  const out = [fmStr({title: 'Contents', description: 'Table of contents — From Industrial Software to AI Agents'})]
  out.push('# Contents\n')
  for (const part of site.en) {
    out.push(`\n## ${part.name}\n`)
    out.push(`\n> ${oneline(part.description)}\n`)
    out.push('')
    for (const ch of part.chapters) {
      const lineTitle = `Chapter ${ch.id}. ${ch.title}`
      if (ch.sections.length) {
        out.push(`- [${lineTitle}](/en/${part.slug}/chapter-${ch.id}/)`)
      } else {
        out.push(`- [${lineTitle}](/${part.slug}/chapter-${ch.id}/) *(Chinese)*`)
      }
    }
  }
  return out.join('\n') + '\n'
}

function renderPreface(info: PageInfo, src: string): string {
  const slug = (info.lang === 'en' ? info.out.slice(3) : info.out).split('/')[1].replace(/\.md$/, '')
  const entry = prefaceTable(info.lang).find(([, s]) => s === slug)
  const fm: Record<string, string> = {title: entry?.[2] ?? slug}
  if (entry?.[3]) fm.description = oneline(entry[3])
  const lastmod = gitLastmod(info.lang)
  if (lastmod) fm.dateModified = lastmod
  return fmStr(fm) + stripFm(src).trimStart()
}

function renderAppendix(info: PageInfo, src: string): string {
  const fm: Record<string, string> = {title: info.lang === 'en' ? 'Appendix' : '附录'}
  const lastmod = gitLastmod(info.lang)
  if (lastmod) fm.dateModified = lastmod
  return fmStr(fm) + stripFm(src).trimStart()
}

// ── 插件入口 ───────────────────────────────────────────────────────────────

/** 纯变换：给定页面路径（重写后或源路径）与源 markdown，返回渲染期等价 markdown。 */
export function transformPage(rel: string, src: string): string {
  const info = classify(rel)
  if (!info) return src
  // Windows 检出（core.autocrlf）会让行尾带 \r，行基正则（shiftHeadings 的 (.+)$ 等）
  // 在 \r 前匹配失败，标题提升会静默失效（H1 出现字面 "##"）；渲染前统一为 \n
  src = src.replace(/\r\n?/g, '\n')
  let next: string
  switch (info.kind) {
    case 'section':
      next = renderSection(info, src)
      break
    case 'chapter':
      next = renderChapter(info)
      break
    case 'part':
      next = renderPart(info)
      break
    case 'contents':
      next = renderContents(info)
      break
    case 'preface':
      next = renderPreface(info, src)
      break
    case 'appendix':
      next = renderAppendix(info, src)
      break
    default:
      return src
  }
  return resolveAnchors(next, info.lang)
}

export function bookMarkdownPlugin(md: MarkdownIt): void {
  // VitePress 1.6 的 frontmatter 由 @mdit-vue 包装 md.render（gray-matter）解析，
  // 先于一切 core 规则；markdown.config 在该包装之后执行，因此再包一层 render
  // 即为最外层 —— 注入的 frontmatter 会被内层正确解析，body 正常渲染。
  const rawRender = md.render.bind(md)
  md.render = ((src: string, env: any = {}) => {
    const rel = String(env?.relativePath ?? env?.path ?? '')
    if (!rel) return rawRender(src, env)
    return rawRender(transformPage(rel, src), env)
  }) as typeof md.render
}
