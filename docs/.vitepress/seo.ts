import type {HeadConfig, TransformContext} from 'vitepress'

const SITE_URL = 'https://book.dc3.site'
const SITE_IMAGE = `${SITE_URL}/cover.png`
const SITE_IMAGE_WIDTH = 2479
const SITE_IMAGE_HEIGHT = 3508
const BOOK_TITLE = '从工业软件到 AI 智能体'
const AUTHOR = '张红元'
const DEFAULT_DESCRIPTION =
  '《从工业软件到 AI 智能体》—— AIoT 技术与实践，从物联网平台到智能体应用。作者张红元，14 章 · 153 张架构图，IoT DC3 开源贯穿全书。'

// 篇名映射：按路由首段还原篇章归属，用于 BreadcrumbList
const PART_BY_SEGMENT: Record<string, {name: string; url: string}> = {
  preface: {name: '卷首', url: '/preface/'},
  foundations: {name: '基础篇', url: '/foundations/'},
  technical: {name: '技术篇', url: '/technical/'},
  applications: {name: '应用篇', url: '/applications/'},
  appendix: {name: '附录', url: '/appendix/'},
}

function routeOf(relativePath: string): string {
  let route = relativePath.replace(/\\/g, '/').replace(/\.md$/, '')
  if (route === 'index') return '/' // 顶级首页归一化，避免 canonical 落到 /index
  route = route.replace(/\/index$/, '/') // 子目录 index → 目录
  return `/${route}`
}

function jsonLd(obj: unknown): HeadConfig {
  return ['script', {type: 'application/ld+json'}, JSON.stringify(obj)]
}

function buildJsonLd(
  relativePath: string,
  canonicalUrl: string,
  title: string,
  description: string,
): HeadConfig[] {
  if (relativePath === 'index.md') {
    return [
      jsonLd({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: BOOK_TITLE,
        url: `${SITE_URL}/`,
        description,
        inLanguage: 'zh-CN',
        publisher: {'@type': 'Person', name: AUTHOR},
      }),
      jsonLd({
        '@context': 'https://schema.org',
        '@type': 'Book',
        name: BOOK_TITLE,
        author: {'@type': 'Person', name: AUTHOR},
        description,
        inLanguage: 'zh-CN',
        image: SITE_IMAGE,
        url: `${SITE_URL}/`,
      }),
    ]
  }

  const segment = relativePath.split('/')[0]
  const part = PART_BY_SEGMENT[segment]
  const itemListElement: object[] = [
    {'@type': 'ListItem', position: 1, name: '首页', item: `${SITE_URL}/`},
  ]
  if (part) {
    itemListElement.push({'@type': 'ListItem', position: 2, name: part.name, item: `${SITE_URL}${part.url}`})
    itemListElement.push({'@type': 'ListItem', position: 3, name: title, item: canonicalUrl})
  } else {
    itemListElement.push({'@type': 'ListItem', position: 2, name: title, item: canonicalUrl})
  }

  return [
    jsonLd({
      '@context': 'https://schema.org',
      '@type': 'Article',
      headline: title,
      description,
      author: {'@type': 'Person', name: AUTHOR},
      inLanguage: 'zh-CN',
      url: canonicalUrl,
      image: SITE_IMAGE,
      isPartOf: {'@type': 'Book', name: BOOK_TITLE, url: `${SITE_URL}/`},
    }),
    jsonLd({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement,
    }),
  ]
}

export function transformHead(context: TransformContext): HeadConfig[] {
  if (context.pageData.isNotFound) {
    return [['meta', {name: 'robots', content: 'noindex,follow'}]]
  }

  const relativePath = context.pageData.relativePath
  const isHome = relativePath === 'index.md'
  const title = context.pageData.title || context.title || BOOK_TITLE
  const fmDesc = context.pageData.frontmatter.description
  const description =
    typeof fmDesc === 'string' && fmDesc.trim() ? fmDesc.trim() : DEFAULT_DESCRIPTION
  const canonicalUrl = new URL(routeOf(relativePath), SITE_URL).href

  return [
    ['meta', {name: 'description', content: description}],
    ['meta', {name: 'robots', content: 'index,follow,max-image-preview:large'}],
    ['meta', {name: 'author', content: AUTHOR}],
    ['link', {rel: 'canonical', href: canonicalUrl}],
    ['meta', {property: 'og:type', content: isHome ? 'book' : 'article'}],
    ['meta', {property: 'og:site_name', content: BOOK_TITLE}],
    ['meta', {property: 'og:title', content: title}],
    ['meta', {property: 'og:description', content: description}],
    ['meta', {property: 'og:url', content: canonicalUrl}],
    ['meta', {property: 'og:image', content: SITE_IMAGE}],
    ['meta', {property: 'og:image:width', content: String(SITE_IMAGE_WIDTH)}],
    ['meta', {property: 'og:image:height', content: String(SITE_IMAGE_HEIGHT)}],
    ['meta', {property: 'og:image:alt', content: `《${BOOK_TITLE}》封面`}],
    ['meta', {property: 'og:locale', content: 'zh_CN'}],
    ['meta', {name: 'twitter:card', content: 'summary_large_image'}],
    ['meta', {name: 'twitter:title', content: title}],
    ['meta', {name: 'twitter:description', content: description}],
    ['meta', {name: 'twitter:image', content: SITE_IMAGE}],
    ...buildJsonLd(relativePath, canonicalUrl, title, description),
  ]
}
