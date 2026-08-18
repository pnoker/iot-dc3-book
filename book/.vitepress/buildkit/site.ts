/**
 * 站点结构中枢：在 config 加载期一次性解析手稿树与篇章配置，
 * 产出 rewrites 映射、双语侧栏、全书小节线性链、图一致性校验。
 *
 * 数据源（唯一权威）：
 *   book/config/parts.yaml | parts-en.yaml  —— 篇章结构（章 id 一一对应）
 *   book/manuscript/{zh,en}/                —— 手稿树（缺章 = 缺目录，回退自然成立）
 *   book/pages/{zh,en}/                     —— 结构页 stub（contents/part/chapter）
 */
import {readFileSync, readdirSync, existsSync} from 'node:fs'
import {join} from 'node:path'
import {execSync} from 'node:child_process'
import YAML from 'yaml'
import {BOOK_DIR, PART_SLUGS, listFigureIds, loadFigureRegistry} from './figures.ts'

export interface Chapter {
  id: number
  title: string
  description: string
  partIndex: number
  partSlug: string
  /** 节文件（按文件名排序）；无手稿目录 → 空数组 */
  sections: Section[]
  hasIntro: boolean
}
export interface Section {
  stem: string // "1.1"
  title: string // "1.1 物联网的定义"
  /** 重写后输出路径（srcDir 相对，含 .md），en 侧含 en/ 前缀 */
  outPath: string
  url: string // "/foundations/chapter-1/1-1"（en 含 /en 前缀）
}
export interface Part {
  name: string
  prefix: string
  description: string
  slug: string
  /** 第几篇（1 起） */
  partIndex: number
  chapters: Chapter[]
}

export type Lang = 'zh' | 'en'

// 卷首单页：(源文件名, 输出 slug, 显示名, frontmatter description)
const PREFACE_ZH: [string, string, string, string][] = [
  ['author.md', 'author', '关于作者',
    'IoT DC3 开源作者张红元——架构师、物联网专家，十余年工业物联网平台研发经验，著有《从工业软件到 AI 智能体》。'],
  ['foreword.md', 'foreword', '序',
    '《从工业软件到 AI 智能体》作者自序——阐述写作初衷、全书定位与技术选型考量。'],
  ['guide.md', 'guide', '导读',
    '《从工业软件到 AI 智能体》阅读指南——按读者角色（入门开发者、架构师、项目经理）推荐最佳阅读路径。'],
]
const PREFACE_EN: [string, string, string, string][] = [
  ['author.md', 'author', 'About the Author',
    'Zhang Hongyuan, creator of the open-source IoT DC3 platform — architect and IoT specialist with over a decade of industrial IoT platform engineering.'],
  ['foreword.md', 'foreword', 'Foreword',
    "The author's foreword to From Industrial Software to AI Agents — why the book was written, what it covers, and the thinking behind its technical choices."],
  ['guide.md', 'guide', 'How to Read This Book',
    'A reading guide to From Industrial Software to AI Agents — recommended paths by reader role: newcomers, platform developers, and AI engineers.'],
]

export function prefaceTable(lang: Lang): [string, string, string, string][] {
  return lang === 'zh' ? PREFACE_ZH : PREFACE_EN
}

function slugOf(partName: string): string {
  const key = partName.split('·')[0].trim() // "基础篇 · ..." → "基础篇"
  const hit = PART_SLUGS[key]
  if (!hit) throw new Error(`未知篇章「${key}」，请在 PART_SLUGS 补充映射。`)
  return hit[0]
}

/** 剥掉 md 头部 frontmatter 块 */
export function stripFrontmatter(md: string): string {
  return md.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, '')
}

/** 解析节文件：提取 H2 节标题（## N.M xxx） */
function parseSectionFile(md: string): {stem: string; title: string} | null {
  const body = stripFrontmatter(md)
  for (const line of body.split('\n')) {
    const m = /^##\s+(.+)$/.exec(line)
    if (m) {
      const title = m[1].trim()
      const stemM = /^(\d+\.\d+)(?=\s|$)/.exec(title)
      return {stem: stemM ? stemM[1] : '', title}
    }
    // H2 之前的非空内容（除 frontmatter）不应出现；继续扫到第一个标题
    if (/^#\s+/.test(line)) break
  }
  return null
}

function sectionUrl(slug: string, cid: number, stem: string, lang: Lang): string {
  const base = `/${slug}/chapter-${cid}/${stem.replace('.', '-')}`
  return lang === 'en' ? `/en${base}` : base
}

function buildLang(lang: Lang, partsCfg: unknown[], zhSlugs?: string[]): Part[] {
  const parts: Part[] = []
  partsCfg.forEach((raw: any, i) => {
    // en 侧 slug 沿用 zh 篇（与旧管线 slug_of(part_zh) 对等，URL 双语同构）
    const slug = lang === 'en' && zhSlugs ? zhSlugs[i] : slugOf(String(raw.name))
    const chapters: Chapter[] = (raw.chapters ?? []).map((ch: any) => {
      const cid = Number(ch.id)
      const chDir = join(BOOK_DIR, 'manuscript', lang, `chapter-${String(cid).padStart(2, '0')}`)
      const sections: Section[] = []
      if (existsSync(chDir)) {
        for (const f of readdirSync(chDir).filter((x) => /^\d+\.\d+\.md$/.test(x)).sort()) {
          const parsed = parseSectionFile(readFileSync(join(chDir, f), 'utf-8'))
          if (parsed?.stem) {
            const outPath =
              lang === 'en'
                ? `en/${slug}/chapter-${cid}/${parsed.stem.replace('.', '-')}.md`
                : `${slug}/chapter-${cid}/${parsed.stem.replace('.', '-')}.md`
            sections.push({...parsed, outPath, url: sectionUrl(slug, cid, parsed.stem, lang)})
          }
        }
      }
      return {
        id: cid,
        title: String(ch.title ?? ''),
        description: String(ch.description ?? ''),
        partIndex: i + 1,
        partSlug: slug,
        sections,
        hasIntro: existsSync(join(chDir, '_intro.md')),
      }
    })
    parts.push({
      name: String(raw.name),
      prefix: String(raw.prefix ?? ''),
      description: String(raw.description ?? ''),
      slug,
      partIndex: i + 1,
      chapters,
    })
  })
  return parts
}

export interface Site {
  zh: Part[]
  en: Part[]
  /** zh 全书小节线性链（供 section-nav） */
  chainZh: {title: string; url: string; outPath: string}[]
  chainEn: {title: string; url: string; outPath: string}[]
  /** 输出路径 → 线性链邻居 */
  navZh: Map<string, {prev?: [string, string]; next?: [string, string]}>
  navEn: Map<string, {prev?: [string, string]; next?: [string, string]}>
}

let _site: Site | null = null

/** 解析并缓存站点结构（config 加载期调用一次）。 */
export function getSite(): Site {
  if (_site) return _site
  const partsZh = buildLang('zh', YAML.parse(readFileSync(join(BOOK_DIR, 'config', 'parts.yaml'), 'utf-8')))
  const partsEnRaw = readFileSync(join(BOOK_DIR, 'config', 'parts-en.yaml'), 'utf-8')
  const partsEn = buildLang('en', YAML.parse(partsEnRaw), partsZh.map((p) => p.slug))
  if (partsZh.length !== partsEn.length) {
    throw new Error(`parts-en.yaml 篇数(${partsEn.length})与 parts.yaml(${partsZh.length})不一致。`)
  }

  const buildChain = (parts: Part[]) => {
    const chain: {title: string; url: string; outPath: string}[] = []
    for (const part of parts) {
      for (const ch of part.chapters) {
        for (const s of ch.sections) chain.push({title: s.title, url: s.url, outPath: s.outPath})
      }
    }
    const nav = new Map<string, {prev?: [string, string]; next?: [string, string]}>()
    chain.forEach((cur, i) => {
      const prev = chain[i - 1]
      const next = chain[i + 1]
      nav.set(cur.outPath, {
        prev: prev ? [prev.title, prev.url] : undefined,
        next: next ? [next.title, next.url] : undefined,
      })
    })
    return {chain, nav}
  }
  const zh = buildChain(partsZh)
  const en = buildChain(partsEn)
  _site = {
    zh: partsZh,
    en: partsEn,
    chainZh: zh.chain,
    chainEn: en.chain,
    navZh: zh.nav,
    navEn: en.nav,
  }
  auditFigures()
  return _site
}

/** 一致性校验：手稿锚点集 == 图源 html 集 == 注册表 yaml 集（fail build，根治静默漂移）。 */
function auditFigures(): void {
  const anchorRe = /@\[(fig-\d{2}-\d{2})\]/g
  const anchors = new Set<string>()
  for (const lang of ['zh', 'en'] as Lang[]) {
    const scan = (dir: string) => {
      if (!existsSync(dir)) return
      for (const f of readdirSync(dir, {withFileTypes: true})) {
        const p = join(dir, f.name)
        if (f.isDirectory()) scan(p)
        else if (f.name.endsWith('.md')) {
          for (const m of readFileSync(p, 'utf-8').matchAll(anchorRe)) anchors.add(m[1])
        }
      }
    }
    scan(join(BOOK_DIR, 'manuscript', lang))
  }
  const htmlIds = new Set(listFigureIds())
  const yamlIds = new Set(
    readdirSync(join(BOOK_DIR, 'figures'), {withFileTypes: true})
      .filter((d) => d.isDirectory() && /^chapter-\d+$/.test(d.name))
      .flatMap((d) =>
        readdirSync(join(BOOK_DIR, 'figures', d.name))
          .filter((f) => f.endsWith('.yaml'))
          .map((f) => f.replace(/\.yaml$/, '')),
      ),
  )
  const diff = (a: Set<string>, b: Set<string>, la: string, lb: string) =>
    [...a].filter((x) => !b.has(x)).map((x) => `  ${x}: 在${la}存在，${lb}缺失`)
  const problems = [
    ...diff(anchors, htmlIds, '手稿锚点', '图源 html'),
    ...diff(htmlIds, anchors, '图源 html', '手稿锚点'),
    ...diff(htmlIds, yamlIds, '图源 html', '注册表 yaml'),
    ...diff(yamlIds, htmlIds, '注册表 yaml', '图源 html'),
  ]
  if (problems.length) {
    throw new Error(`图一致性校验失败（手稿锚点 / 图源 / 注册表三方不一致）：\n${problems.join('\n')}`)
  }
}

// ── rewrites ───────────────────────────────────────────────────────────────

/** 手稿源路径（srcDir 相对）→ 输出路径；返回 undefined 表示保持原样。 */
export function rewrite(id: string): string | undefined {
  const site = getSite()

  // 手写站页与结构页之外的中文侧
  // manuscript/zh/preface/{slug}.md → preface/{slug}.md
  let m = /^manuscript\/zh\/preface\/([\w-]+)\.md$/.exec(id)
  if (m) return `preface/${m[1]}.md`
  // manuscript/zh/chapter-XX/X.Y.md → {slug}/chapter-N/X-Y.md
  m = /^manuscript\/zh\/chapter-(\d+)\/(\d+)\.(\d+)\.md$/.exec(id)
  if (m) {
    const cid = Number(m[1])
    const part = partOf(site.zh, cid)
    if (part) return `${part.slug}/chapter-${cid}/${m[2]}-${m[3]}.md`
  }
  // manuscript/zh/appendix.md → appendix/index.md
  if (id === 'manuscript/zh/appendix.md') return 'appendix/index.md'

  // pages/zh/ 结构页 stub
  if (id === 'pages/zh/contents.md') return 'preface/contents.md'
  m = /^pages\/zh\/part-(\d+)\.md$/.exec(id)
  if (m) {
    const part = site.zh[Number(m[1]) - 1]
    if (part) return `${part.slug}/index.md`
  }
  m = /^pages\/zh\/chapter-(\d+)\.md$/.exec(id)
  if (m) {
    const cid = Number(m[1])
    const part = partOf(site.zh, cid)
    if (part) return `${part.slug}/chapter-${cid}/index.md`
  }

  // 英文侧：同构 + en/ 前缀（en 章无手稿 → 无节页；章 stub 文件不存在即不生成）
  m = /^manuscript\/en\/preface\/([\w-]+)\.md$/.exec(id)
  if (m) return `en/preface/${m[1]}.md`
  m = /^manuscript\/en\/chapter-(\d+)\/(\d+)\.(\d+)\.md$/.exec(id)
  if (m) {
    const cid = Number(m[1])
    const part = partOf(site.en, cid)
    if (part) return `en/${part.slug}/chapter-${cid}/${m[2]}-${m[3]}.md`
  }
  if (id === 'manuscript/en/appendix.md') return 'en/appendix/index.md'

  if (id === 'pages/en/contents.md') return 'en/preface/contents.md'
  m = /^pages\/en\/part-(\d+)\.md$/.exec(id)
  if (m) {
    const part = site.en[Number(m[1]) - 1]
    if (part) return `en/${part.slug}/index.md`
  }
  m = /^pages\/en\/chapter-(\d+)\.md$/.exec(id)
  if (m) {
    const cid = Number(m[1])
    const part = partOf(site.en, cid)
    if (part) return `en/${part.slug}/chapter-${cid}/index.md`
  }
  return undefined
}

function partOf(parts: Part[], cid: number): Part | undefined {
  return parts.find((p) => p.chapters.some((c) => c.id === cid))
}

// ── sidebar ────────────────────────────────────────────────────────────────

export interface SidebarItem {
  text: string
  link?: string
  collapsed?: boolean
  items?: SidebarItem[]
}

export function sidebarZh(): SidebarItem[] {
  const site = getSite()
  const prefaceItems: SidebarItem[] = []
  for (const [, slug, label] of prefaceTable('zh')) {
    if (existsSync(join(BOOK_DIR, 'manuscript', 'zh', 'preface', `${slug}.md`))) {
      prefaceItems.push({text: label, link: `/preface/${slug}`})
    }
  }
  prefaceItems.push({text: '目录', link: '/preface/contents'})
  const out: SidebarItem[] = [{text: '卷首', items: prefaceItems}]
  for (const part of site.zh) {
    const items: SidebarItem[] = []
    for (const ch of part.chapters) {
      const title = `第 ${ch.id} 章　${ch.title}`
      const link = `/${part.slug}/chapter-${ch.id}/`
      const secItems = ch.sections.map((s) => ({text: s.title, link: s.url}))
      if (secItems.length) {
        items.push({text: title, link, collapsed: true, items: secItems})
      } else {
        items.push({text: title, link})
      }
    }
    out.push({text: part.name, collapsed: false, items})
  }
  out.push({text: '附录', link: '/appendix/'})
  out.push({text: '版权与许可', link: '/copyright'})
  return out
}

export function sidebarEn(): SidebarItem[] {
  const site = getSite()
  const prefaceItems: SidebarItem[] = []
  for (const [, slug, label] of prefaceTable('en')) {
    if (existsSync(join(BOOK_DIR, 'manuscript', 'en', 'preface', `${slug}.md`))) {
      prefaceItems.push({text: label, link: `/en/preface/${slug}`})
    }
  }
  prefaceItems.push({text: 'Contents', link: '/en/preface/contents'})
  const out: SidebarItem[] = [{text: 'Front Matter', items: prefaceItems}]
  for (const part of site.en) {
    const items: SidebarItem[] = []
    for (const ch of part.chapters) {
      const title = `Chapter ${ch.id}. ${ch.title}`
      if (!ch.sections.length) {
        items.push({text: title}) // 未翻译章：无 link 纯文本条目
        continue
      }
      const link = `/en/${part.slug}/chapter-${ch.id}/`
      items.push({
        text: title,
        link,
        collapsed: true,
        items: ch.sections.map((s) => ({text: s.title, link: s.url})),
      })
    }
    out.push({text: part.name, collapsed: false, items})
  }
  if (existsSync(join(BOOK_DIR, 'manuscript', 'en', 'appendix.md'))) {
    out.push({text: 'Appendix', link: '/en/appendix/'})
  } else {
    out.push({text: 'Appendix'})
  }
  out.push({text: 'Copyright & License', link: '/en/copyright'})
  return out
}

// ── lastmod（卷首/附录 frontmatter dateModified）──────────────────────────

const _lastmod = new Map<Lang, string>()

/** 指定语言手稿树最近一次提交的 ISO 日期（缓存；路径无提交记录时回退到最后一次提交）。 */
export function gitLastmod(lang: Lang): string {
  const hit = _lastmod.get(lang)
  if (hit !== undefined) return hit
  let out = ''
  try {
    out = execSync(
      `git log -1 --format=%aI -- book/manuscript/${lang}`,
      {cwd: join(BOOK_DIR, '..'), timeout: 5000},
    ).toString().trim()
  } catch {
    /* 路径暂无提交（如未提交的目录迁移），继续回退 */
  }
  if (!out) {
    try {
      out = execSync('git log -1 --format=%aI', {cwd: join(BOOK_DIR, '..'), timeout: 5000})
        .toString().trim()
    } catch {
      out = ''
    }
  }
  _lastmod.set(lang, out)
  return out
}

// ── 插图清单（图库页数据源）────────────────────────────────────────────────

const ANCHOR_RE = /@\[(fig-\d{2}-\d{2})\]/g

function fixCaption(alt: string): string {
  return alt.replace(/图(\d)/g, '图 $1')
}

/** 注册表 title 的英文回退：精确键 → 去空格归一 → 图 N-M 前缀。 */
export function figureTitleEn(figId: string, reg: Record<string, unknown>): string | null {
  const labelsEn = ((reg.labels as Record<string, unknown> | undefined)?.en ?? {}) as Record<string, string>
  const title = String(reg.title ?? '')
  if (title in labelsEn) return labelsEn[title]
  const norm = (x: string) => x.replace(/\s+/g, '')
  for (const [k, v] of Object.entries(labelsEn)) {
    if (norm(k) === norm(title)) return v
  }
  const [, chNo, figNo] = figId.split('-')
  const prefixRe = new RegExp(`^图\\s*${Number(chNo)}-${Number(figNo)}\\b`)
  for (const [k, v] of Object.entries(labelsEn)) {
    if (prefixRe.test(k)) return v
  }
  return null
}

/** 生成全书插图清单（等价旧 gen_figures_manifest：扫手稿锚点 + 结构数据计算 url）。 */
export function genFiguresManifest(): unknown[] {
  const site = getSite()
  const chapterTitleEn = new Map<number, string>()
  for (const part of site.en) {
    for (const ch of part.chapters) chapterTitleEn.set(ch.id, ch.title)
  }
  const manifest: unknown[] = []
  for (const part of site.zh) {
    for (const ch of part.chapters) {
      const chDir = join(BOOK_DIR, 'manuscript', 'zh', `chapter-${String(ch.id).padStart(2, '0')}`)
      if (!existsSync(chDir)) continue
      for (const f of readdirSync(chDir).filter((x) => /^\d+\.\d+\.md$/.test(x)).sort()) {
        const md = readFileSync(join(chDir, f), 'utf-8')
        const stem = f.replace(/\.md$/, '')
        const url = sectionUrl(part.slug, ch.id, stem, 'zh')
        for (const m of md.matchAll(ANCHOR_RE)) {
          const figId = m[1]
          const reg = loadFigureRegistry(figId)
          const titleSrc = String(reg.title ?? '')
          const mNum = /^(图\s*\d+-\d+)\s*(.*)/.exec(titleSrc)
          const num = mNum ? fixCaption(mNum[1]) : ''
          const title = mNum ? mNum[2].trim() : titleSrc
          const [, chNo, figNo] = figId.split('-')
          manifest.push({
            id: figId,
            num,
            numEn: `Figure ${Number(chNo)}-${Number(figNo)}`,
            title,
            titleEn: figureTitleEn(figId, reg) ?? title,
            chapter: ch.id,
            chapterTitle: ch.title,
            chapterTitleEn: chapterTitleEn.get(ch.id) ?? ch.title,
            url: url + '#' + figId,
            thumb: '',
          })
        }
      }
    }
  }
  return manifest
}
