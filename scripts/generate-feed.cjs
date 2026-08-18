#!/usr/bin/env node
/**
 * 生成 Atom / RSS feed — VitePress 原生不支持，此脚本在构建后运行。
 *
 * 输入: book/.vitepress/dist/sitemap.xml + book/config/parts.yaml
 * 输出: book/.vitepress/dist/feed.xml (Atom 1.0)
 *
 * 用途: RSS 阅读器订阅、搜索引擎 feed 发现、内容聚合平台抓取。
 */

const { readFileSync, writeFileSync } = require('node:fs')
const { join } = require('node:path')
const { execSync } = require('node:child_process')

const ROOT = join(__dirname, '..')
const DIST = join(ROOT, 'book', '.vitepress', 'dist')

const SITE_URL = 'https://book.dc3.site'
const BOOK_TITLE = '从工业软件到 AI 智能体'
const BOOK_DESC = 'AIoT 技术与实践 —— 从物联网平台到智能体应用'
const AUTHOR_NAME = '张红元'
const AUTHOR_EMAIL = 'pnoker@dc3.site'

function lastmod() {
  let d
  try {
    d = execSync('git log -1 --format=%aI', { cwd: ROOT, timeout: 5000 }).toString().trim()
  } catch {}
  return d || new Date().toISOString()
}

const updated = lastmod()

// Parse sitemap to get all URLs
let urls = []
try {
  const sitemap = readFileSync(join(DIST, 'sitemap.xml'), 'utf-8')
  const re = /<loc>([^<]+)<\/loc>/g
  let m
  while ((m = re.exec(sitemap)) !== null) {
    urls.push(m[1])
  }
} catch {
  console.error('⚠️  sitemap.xml not found, skipping feed generation')
  process.exit(0)
}

if (urls.length === 0) {
  console.error('⚠️  no URLs in sitemap, skipping feed generation')
  process.exit(0)
}

// Build Atom feed entries
const entries = urls.map((url) => {
  const pathname = new URL(url).pathname
  const isChapter = /\bchapter-\d+\b/.test(pathname)
  let title = pathname === '/' ? BOOK_TITLE : pathname.replace(/\//g, ' ').trim().replace(/-/g, ' ')
  // Extract chapter number for nicer titles
  const chMatch = pathname.match(/chapter-(\d+)/)
  if (chMatch) title = `第 ${parseInt(chMatch[1])} 章`
  if (pathname === '/preface/author') title = '关于作者'
  if (pathname === '/preface/foreword') title = '序'
  if (pathname === '/preface/guide') title = '导读'
  if (pathname === '/preface/contents') title = '全书目录'
  if (pathname === '/appendix/') title = '附录'

  return `  <entry>
    <title>${escapeXml(title)}</title>
    <link href="${escapeXml(url)}" rel="alternate" type="text/html"/>
    <id>${escapeXml(url)}</id>
    <updated>${updated}</updated>
    <author><name>${AUTHOR_NAME}</name></author>
  </entry>`
})

const feed = `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>${SITE_URL}/</id>
  <title>${escapeXml(BOOK_TITLE)}</title>
  <subtitle>${escapeXml(BOOK_DESC)}</subtitle>
  <updated>${updated}</updated>
  <author>
    <name>${AUTHOR_NAME}</name>
    <email>${AUTHOR_EMAIL}</email>
  </author>
  <link href="${SITE_URL}/" rel="alternate" type="text/html"/>
  <link href="${SITE_URL}/feed.xml" rel="self" type="application/atom+xml"/>
  <rights>© ${new Date().getFullYear()} ${AUTHOR_NAME}</rights>
  <generator>book.dc3.site feed generator</generator>
${entries.join('\n')}
</feed>
`

writeFileSync(join(DIST, 'feed.xml'), feed)
console.log(`  ✅ feed.xml generated: ${urls.length} entries`)

function escapeXml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}
