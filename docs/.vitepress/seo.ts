import type {HeadConfig, TransformContext} from 'vitepress'

const SITE_URL = 'https://book.dc3.site'
const SITE_IMAGE = `${SITE_URL}/cover.png`
const DEFAULT_DESCRIPTION =
  '《从工业软件到 AI 智能体》—— AIoT 技术与实践，从物联网平台到智能体应用。作者张红元，14 章 · 72 张架构图，IoT DC3 开源贯穿全书。'

function routeOf(relativePath: string): string {
  const route = relativePath
    .replace(/\\/g, '/')
    .replace(/\.md$/, '')
    .replace(/\/index$/, '/')
  return route ? `/${route}` : '/'
}

export function transformHead(context: TransformContext): HeadConfig[] {
  if (context.pageData.isNotFound) {
    return [['meta', {name: 'robots', content: 'noindex,follow'}]]
  }

  const title = context.pageData.title || context.title || '从工业软件到 AI 智能体'
  const fmDesc = context.pageData.frontmatter.description
  const description =
    typeof fmDesc === 'string' && fmDesc.trim() ? fmDesc.trim() : DEFAULT_DESCRIPTION
  const canonicalUrl = new URL(routeOf(context.pageData.relativePath), SITE_URL).href

  return [
    ['meta', {name: 'description', content: description}],
    ['meta', {name: 'robots', content: 'index,follow,max-image-preview:large'}],
    ['meta', {name: 'author', content: '张红元'}],
    ['link', {rel: 'canonical', href: canonicalUrl}],
    ['meta', {property: 'og:type', content: 'book'}],
    ['meta', {property: 'og:site_name', content: '从工业软件到 AI 智能体'}],
    ['meta', {property: 'og:title', content: title}],
    ['meta', {property: 'og:description', content: description}],
    ['meta', {property: 'og:url', content: canonicalUrl}],
    ['meta', {property: 'og:image', content: SITE_IMAGE}],
    ['meta', {property: 'og:locale', content: 'zh_CN'}],
    ['meta', {name: 'twitter:card', content: 'summary_large_image'}],
    ['meta', {name: 'twitter:title', content: title}],
    ['meta', {name: 'twitter:description', content: description}],
    ['meta', {name: 'twitter:image', content: SITE_IMAGE}],
  ]
}
