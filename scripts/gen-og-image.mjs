#!/usr/bin/env node
/**
 * 从 public/og-image.svg 渲染 og-image.png（1200×630 横版社交卡片）。
 * 运行: pnpm gen:og（需本机已安装 Google Chrome / Edge）
 * PNG 为提交产物；仅当 SVG 变更后需重新生成本地执行并提交。
 */
import {execSync} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {dirname, join} from 'node:path'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const svg = join(root, 'docs', 'public', 'og-image.svg')
const png = join(root, 'docs', 'public', 'og-image.png')

const candidates = [
  process.env.CHROME_BIN,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  'google-chrome',
  'chromium',
  'chromium-browser'
].filter(Boolean)

const bin = candidates.find(p => {
  if (p.includes('/')) {
    try { execSync(`test -x "${p}"`); return true } catch { return false }
  }
  return true
})

if (!bin) {
  console.error('❌ 未找到 Chrome/Edge，请安装后重试，或设置 CHROME_BIN 环境变量')
  process.exit(1)
}

execSync(
  `"${bin}" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --user-data-dir=/tmp/dc3-og-chrome --window-size=1200,630 --screenshot="${png}" "file://${svg}"`,
  {stdio: 'inherit'}
)
console.log(`✅ og-image.png generated → ${png}`)
