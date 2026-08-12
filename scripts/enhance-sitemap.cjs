#!/usr/bin/env node
/**
 * VitePress 构建后脚本：增强 sitemap.xml（lastmod + priority）。
 *
 * VitePress 内置 sitemap 只输出 <loc>，Google 建议补充 <lastmod> 以优化抓取效率。
 * 此脚本在 `vitepress build` 之后运行，由 package.json build 脚本串联。
 */

const { readFileSync, writeFileSync } = require('node:fs')
const { join } = require('node:path')

const distDir = join(__dirname, '..', 'docs', '.vitepress', 'dist')
const sitemapPath = join(distDir, 'sitemap.xml')

let xml
try {
  xml = readFileSync(sitemapPath, 'utf-8')
} catch {
  console.error('⚠️  sitemap.xml 未找到，跳过增强')
  process.exit(0)
}

// 以构建当天为 lastmod（每次部署即内容更新）
const lastmod = new Date().toISOString().split('T')[0]

/** 根据路由计算 sitemap priority */
function priorityOf(route) {
  if (route === '/') return '1.0'
  if (/\bchapter-\d+\b/.test(route)) return '0.9'
  if (/^\/(foundations|technical|applications)\/$/.test(route)) return '0.8'
  if (/^\/preface\//.test(route)) return '0.7'
  if (/^\/appendix\//.test(route)) return '0.6'
  return '0.5'
}

let count = 0
xml = xml.replace(/<url><loc>([^<]+)<\/loc><\/url>/g, (_, url) => {
  const route = new URL(url).pathname
  const priority = priorityOf(route)
  count++
  return `<url><loc>${url}</loc><lastmod>${lastmod}</lastmod><priority>${priority}</priority></url>`
})

writeFileSync(sitemapPath, xml)
console.log(`  ✅ sitemap enhanced: ${count} URLs + lastmod + priority`)
