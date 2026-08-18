#!/usr/bin/env node
/**
 * 抽取插图 SVG 内的中文文本，生成/补全图注册表的英文标注（labels.en）。
 *
 * 图注册表：book/figures/chapter-XX/{fig-id}.yaml（spec + caption.zh/en + labels.en）。
 * 改图后重跑本脚本可同步 labels.en 的键（已有译文保留，新增键留空待译）。
 *
 * 用法:
 *   node scripts/figure-i18n.mjs fig-01-05            # 打印该图的 labels.en 桩
 *   node scripts/figure-i18n.mjs fig-01-05 --write    # 写入注册表（不覆盖已填译文）
 *   node scripts/figure-i18n.mjs chapter-01 --write   # 整章批量
 */
import {readFileSync, writeFileSync, readdirSync, existsSync} from 'node:fs'
import {join, dirname, resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
import YAML from 'yaml'

const BOOK = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'book')
const figs = await import(join(BOOK, '.vitepress/buildkit/figures.ts'))
const FIGURES_DIR = figs.FIGURES_DIR
const {loadFigureRegistry, extractFigureTexts} = figs

const target = process.argv[2]
const doWrite = process.argv.includes('--write')
if (!target) {
  console.error('用法: node scripts/figure-i18n.mjs <fig-XX-YY | chapter-XX> [--write]')
  process.exit(1)
}

function figureHtml(figId) {
  const chapter = figId.split('-')[1]
  const p = join(FIGURES_DIR, `chapter-${chapter}`, `${figId}.html`)
  return existsSync(p) ? readFileSync(p, 'utf-8') : null
}

function figIdsOf(chapter) {
  const no = String(parseInt(chapter.replace('chapter-', '').replace('ch', ''), 10)).padStart(2, '0')
  const dir = join(FIGURES_DIR, `chapter-${no}`)
  return readdirSync(dir).filter((f) => /^fig-.*\.html$/.test(f)).map((f) => f.replace(/\.html$/, '')).sort()
}

function yamlStr(text) {
  return '"' + text.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"'
}

function labelsEnOf(reg) {
  const labels = reg.labels
  return labels && typeof labels === 'object' && labels.en && typeof labels.en === 'object'
    ? labels.en : {}
}

function stubYaml(figId) {
  const reg = loadFigureRegistry(figId)
  const labels = labelsEnOf(reg)
  const html = figureHtml(figId)
  const lines = [`# ${figId} labels.en —— 图内标注翻译（键为 SVG 中文原文，改图后重跑本脚本同步）`]
  for (const zh of extractFigureTexts(html ?? '')) {
    lines.push(`${yamlStr(zh)}: ${yamlStr(labels[zh] ?? '')}`)
  }
  return lines.join('\n') + '\n'
}

function writeStub(figId) {
  const regPath = join(FIGURES_DIR, `chapter-${figId.split('-')[1]}`, `${figId}.yaml`)
  if (!existsSync(regPath)) {
    console.error(`✗ 无注册表: ${regPath}`)
    return false
  }
  const reg = loadFigureRegistry(figId)
  const labels = labelsEnOf(reg)
  const html = figureHtml(figId)
  const texts = extractFigureTexts(html ?? '')
  if (texts.every((t) => t in labels)) return false // 无新增条目
  reg.labels = reg.labels ?? {}
  const next = {}
  for (const zh of texts) next[zh] = labels[zh] ?? ''
  reg.labels.en = next
  writeFileSync(regPath, YAML.stringify(reg, {lineWidth: 10000}), 'utf-8')
  return true
}

const targets = /^fig-\d{2}-\d{2}$/.test(target) ? [target] : figIdsOf(target)
for (const figId of targets) {
  if (doWrite) {
    const changed = writeStub(figId)
    console.log(`${changed ? '✓ 更新' : '· 无变化'}  ${figId} labels.en`)
  } else {
    console.log(stubYaml(figId))
  }
}
