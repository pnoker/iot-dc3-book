/**
 * 构建产物生成与 vite 插件：figures.css / 图库三 JSON / divider.css /
 * cover.css / cover-art.ts / cover.png，全部在 config 加载期同步产出。
 *
 * 审计（fail build，根治静默回归）：
 *   - 色值覆盖：COLOR_MAP 未覆盖的色值会让 var(--fig-*) 未定义，明暗主题显示异常；
 *   - 英文残留中文：en 版 SVG 内仍含中文标注（labels.en 缺译文或替换走样）。
 *
 * dev 模式：watch 图源/扉页/配置/封面变更 → 再生产物 + touch config 触发
 * vitepress 全重启（markdown 渲染缓存按 {src,file} 键控，全重启最可靠）。
 */
import {readFileSync, writeFileSync, copyFileSync, existsSync, utimesSync} from 'node:fs'
import {join} from 'node:path'
import type {Plugin} from 'vite'
import {
  BOOK_DIR,
  loadFigureSvg,
  listFigureIds,
  readAllFigureHtmls,
  collectRgbaHexes,
  genFiguresCss,
  jsonDumpsPy,
  figureScopedStyles,
  auditColorCoverage,
  hasCjk,
} from './figures.ts'
import {getSite, genFiguresManifest} from './site.ts'
import {scopeDividerCss, renderCoverInline} from './divider.ts'

const PUBLIC_DIR = join(BOOK_DIR, 'public')
const THEME_DIR = join(BOOK_DIR, '.vitepress', 'theme')

/** 生成全部 public/theme 派生产物并跑两个审计（fail build）。 */
export function prepareAssets(): void {
  getSite() // 触发结构解析与三方一致性校验

  // 封面 PNG（og:image）：静态资产，改 cover.html 后手动重渲染
  const coverPng = join(BOOK_DIR, 'assets', 'cover.png')
  if (existsSync(coverPng)) {
    copyFileSync(coverPng, join(PUBLIC_DIR, 'cover.png'))
  } else {
    throw new Error('缺少 book/assets/cover.png（og:image 将失效）')
  }

  // 审计 1：色值覆盖
  const htmls = readAllFigureHtmls()
  const missing = auditColorCoverage(htmls)
  const missingKeys = Object.keys(missing)
  if (missingKeys.length) {
    const lines = missingKeys
      .sort()
      .map((hexv) => `    ${hexv}: ${[...new Set(missing[hexv])].sort().join(', ')}`)
      .join('\n')
    throw new Error(
      `插图存在 COLOR_MAP 未覆盖的色值（明暗主题会显示异常，请补全 buildkit/figures.ts 的 COLOR_MAP）：\n${lines}`,
    )
  }

  // 全书插图 theme 化 SVG（正文渲染期内联 + 图库页 JSON 数据，同一变换来源）
  const svgMap: Record<string, string> = {}
  const svgMapEn: Record<string, string> = {}
  for (const id of listFigureIds()) {
    svgMap[id] = loadFigureSvg(id, 'zh') ?? ''
    svgMapEn[id] = loadFigureSvg(id, 'en') ?? svgMap[id]
  }
  writeFileSync(join(PUBLIC_DIR, 'figures-svg.json'), jsonDumpsPy(svgMap), 'utf-8')
  writeFileSync(join(PUBLIC_DIR, 'figures-svg-en.json'), jsonDumpsPy(svgMapEn), 'utf-8')

  // 审计 2：英文版残留中文标注
  const unresolved = listFigureIds().filter((id) => svgMapEn[id] && hasCjk(svgMapEn[id]))
  if (unresolved.length) {
    throw new Error(
      `英文版以下插图仍含中文标注（补注册表 labels.en 映射后重跑）：\n    ${unresolved.join('\n    ')}`,
    )
  }

  // 插图主题变量表 + SVG 内 <style> 作用域化规则
  writeFileSync(
    join(PUBLIC_DIR, 'figures.css'),
    genFiguresCss(collectRgbaHexes(htmls)) + '\n' + [...new Set([...collectScopedStyles()])].sort().join('\n'),
    'utf-8',
  )

  // 图库清单（扫手稿锚点 + 结构数据计算 url，与旧产物等价）
  writeFileSync(
    join(PUBLIC_DIR, 'figures-manifest.json'),
    JSON.stringify(genFiguresManifest(), null, 2),
    'utf-8',
  )

  // 章/篇扉页主题样式（作用域化到 .divider-body）
  const dividerCssPath = join(BOOK_DIR, 'dividers', 'divider.css')
  if (existsSync(dividerCssPath)) {
    writeFileSync(
      join(PUBLIC_DIR, 'divider.css'),
      scopeDividerCss(readFileSync(dividerCssPath, 'utf-8')),
      'utf-8',
    )
  }

  // 封面主题样式 + 内联 body（hero 主视觉，跟随明暗主题）
  const [coverCss, coverBody] = renderCoverInline()
  writeFileSync(join(PUBLIC_DIR, 'cover.css'), coverCss, 'utf-8')
  writeFileSync(
    join(THEME_DIR, 'cover-art.ts'),
    '// 自动生成，请勿手改 —— 由 book/.vitepress/buildkit/assets.ts 产出\n'
      + `export const coverBodyHtml = ${JSON.stringify(coverBody)}\n`,
    'utf-8',
  )
}

/** 渲染期 loadFigureSvg 收集的 SVG 内 <style> 作用域化规则。 */
function collectScopedStyles(): string[] {
  // 触发全部图的样式收集（loadFigureSvg 内部写入 figureScopedStyles）
  for (const id of listFigureIds()) loadFigureSvg(id)
  return [...figureScopedStyles.values()]
}

/** vite 插件：dev 下监听图源/扉页/配置/封面，变更后再生产物并触发全重启。 */
export function bookAssetsPlugin(): Plugin {
  return {
    name: 'book-assets',
    configureServer(server) {
      const watched = [
        join(BOOK_DIR, 'figures'),
        join(BOOK_DIR, 'dividers'),
        join(BOOK_DIR, 'config'),
        join(BOOK_DIR, 'assets'),
      ]
      for (const dir of watched) server.watcher.add(dir)
      server.watcher.on('change', (file: string) => {
        if (!watched.some((dir) => file.startsWith(dir))) return
        console.log(`[book] 源变更，再生产物：${file}`)
        try {
          prepareAssets()
          // markdown 渲染缓存按 {src,file} 键控，touch config 触发 vitepress 全重启最可靠
          const configFile = join(BOOK_DIR, '.vitepress', 'config.ts')
          const now = new Date()
          utimesSync(configFile, now, now)
        } catch (err) {
          console.error('[book] 产物再生失败：', err)
        }
      })
    },
  }
}
