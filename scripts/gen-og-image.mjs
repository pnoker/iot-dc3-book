#!/usr/bin/env node
/**
 * 从 public/og-image.svg 渲染 og-image.png（1200×630 横版社交卡片）。
 * 运行: pnpm gen:og（需本机已安装 Google Chrome / Edge）
 * PNG 为提交产物；仅当 SVG 变更后需重新生成本地执行并提交。
 */
import {execSync} from 'node:child_process'
import {existsSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {dirname, join} from 'node:path'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const svg = join(root, 'book', 'public', 'og-image.svg')
const png = join(root, 'book', 'public', 'og-image.png')

const candidates = [
  process.env.CHROME_BIN,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  'google-chrome',
  'chromium',
  'chromium-browser'
].filter(Boolean)

const bin = candidates.find(p => (p.includes('/') || p.includes('\\')) ? existsSync(p) : true)

if (!bin) {
  console.error('❌ 未找到 Chrome/Edge，请安装后重试，或设置 CHROME_BIN 环境变量')
  process.exit(1)
}

try {
  execSync(
    `"${bin}" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --user-data-dir=/tmp/dc3-og-chrome --window-size=1200,630 --screenshot="${png}" "file://${svg}"`,
    // Windows 上 headless 截图完成后进程可能不退出，超时后 PNG 其实已写完
    {stdio: 'inherit', timeout: 90_000}
  )
} catch (error) {
  if (!existsSync(png)) throw error
  console.log('(browser stayed open after screenshot; PNG written, continuing)')
}
console.log(`✅ og-image.png generated → ${png}`)
