#!/usr/bin/env node
/**
 * 生成 llms-full.txt —— llms.txt 的全量正文版，供 LLM 深度索引（AEO）。
 * 在 `vitepress build` 之后运行：扫 book/ 手稿树与结构页 stub，
 * 经 buildkit 同一渲染期变换生成「标题 + 正文全文」，逐页输出。
 * 输出到 dist（随站点部署），手稿是单一事实来源，无需另维护。
 */
import {readFileSync, writeFileSync, readdirSync, statSync, mkdirSync} from 'node:fs'
import {join, relative, resolve, dirname} from 'node:path'
import {fileURLToPath} from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const BOOK = join(ROOT, 'book')
const OUT = join(BOOK, '.vitepress/dist/llms-full.txt')
const SITE_URL = 'https://book.dc3.site'

// 与 config.ts srcExclude 一致（不出页的 md）
const EXCLUDE_REL = new Set([
  'WRITING_GUIDE.md',
  'manuscript/README.md',
  'manuscript/TRANSLATION_CONTRACT.md',
])
const EXCLUDE_DIRS = new Set(['.vitepress', 'public', 'node_modules', 'design', 'assets', 'config', 'dividers', 'figures'])

const {transformPage} = await import(join(BOOK, '.vitepress/buildkit/markdown.ts'))
const {rewrite} = await import(join(BOOK, '.vitepress/buildkit/site.ts'))

function walk(dir, out = []) {
  let entries = []
  try { entries = readdirSync(dir) } catch { return out }
  entries.sort()
  for (const name of entries) {
    if (name.startsWith('.') || EXCLUDE_DIRS.has(name)) continue
    const full = join(dir, name)
    const st = statSync(full)
    if (st.isDirectory()) walk(full, out)
    else if (name.endsWith('.md') && !name.startsWith('_')) out.push(full)
  }
  return out
}

function urlOf(srcRel) {
  const outRel = rewrite(srcRel) ?? srcRel
  let rel = outRel.replace(/\\/g, '/').replace(/\.md$/, '')
  if (rel === 'index') return `${SITE_URL}/`
  if (rel.endsWith('/index')) return `${SITE_URL}/${rel.slice(0, -6)}/`
  return `${SITE_URL}/${rel}`
}

function parse(src) {
  let title = ''
  let body = src
  const fm = src.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/)
  if (fm) {
    const t = fm[1].match(/^title:\s*(.+)$/m)
    if (t) title = t[1].trim().replace(/^['"]|['"]$/g, '')
    body = src.slice(fm[0].length)
  }
  body = body.trim()
  if (!title) {
    const h = body.match(/^#\s+(.+)$/m)
    if (h) title = h[1].trim()
  }
  // 去掉与标题重复的首个 H1，避免正文里再出现一次标题
  body = body.replace(/^#\s+[^\n]*\n?/, '').trim()
  return {title: title || 'Untitled', body}
}

const files = walk(BOOK).filter((f) => {
  const rel = relative(BOOK, f).replace(/\\/g, '/')
  return !EXCLUDE_REL.has(rel) && !/\/_intro\.md$/.test(rel)
})

// 版权头：置于全文最前，确保 LLM 深度索引时归属信息恒在（复制/抓取也不丢失作者）
const HEADER = [
  '# 从工业软件到 AI 智能体',
  '',
  '> 作者：张红元（IoT DC3 开源作者 · 架构师 · 物联网专家）',
  '',
  '《从工业软件到 AI 智能体》由张红元著，© 2016–2026 张红元，保留所有权利。',
  '',
  '- 在线阅读：https://book.dc3.site',
  '- 开源项目：IoT DC3（https://github.com/pnoker/iot-dc3）',
  '- 引用与转载：请注明作者「张红元」、书名与章节号，并附来源链接。未经许可不得商用、不得演绎。',
  '',
  '---',
  '',
].join('\n')

const parts = []
for (const file of files) {
  const rel = relative(BOOK, file).replace(/\\/g, '/')
  const transformed = transformPage(rel, readFileSync(file, 'utf-8'))
  const {title, body} = parse(transformed)
  parts.push(`# ${title}\n\nURL: ${urlOf(rel)}\n\n${body}\n\n---\n`)
}

mkdirSync(dirname(OUT), {recursive: true})
writeFileSync(OUT, HEADER + '\n' + parts.join('\n'), 'utf-8')
console.log(`  ✅ llms-full.txt generated: ${files.length} pages → ${OUT}`)
