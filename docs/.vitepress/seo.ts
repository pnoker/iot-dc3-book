import type {HeadConfig, TransformContext} from 'vitepress'

const SITE_URL = 'https://book.dc3.site'
const SITE_IMAGE = `${SITE_URL}/cover.png`
const SITE_IMAGE_WIDTH = 2479
const SITE_IMAGE_HEIGHT = 3508
const BOOK_TITLE = '从工业软件到 AI 智能体'
const BOOK_SUBTITLE = '构建面向智能场景演进的多协议、云原生、AI Native 工业物联网平台'
const AUTHOR = '张红元'
const TWITTER_CREATOR = '@iotdc3'
const BOOK_DATE_PUBLISHED = '2025-06-01'
const DEFAULT_DESCRIPTION =
  '《从工业软件到 AI 智能体》—— AIoT 技术与实践，从物联网平台到智能体应用。作者张红元，14 章 · 155 张架构图，IoT DC3 开源贯穿全书。'

const SCHEMA = 'https://schema.org'

const PART_BY_SEGMENT: Record<string, {name: string; url: string}> = {
  preface: {name: '卷首', url: '/preface/'},
  foundations: {name: '基础篇', url: '/foundations/'},
  technical: {name: '技术篇', url: '/technical/'},
  applications: {name: '应用篇', url: '/applications/'},
  appendix: {name: '附录', url: '/appendix/'},
}

/* ── 工具 ─────────────────────────────────────────────────────────── */

function routeOf(relativePath: string): string {
  let route = relativePath.replace(/\\/g, '/').replace(/\.md$/, '')
  if (route === 'index') return '/'
  route = route.replace(/\/index$/, '/')
  return `/${route}`
}

function jsonLd(obj: unknown): HeadConfig {
  return ['script', {type: 'application/ld+json'}, JSON.stringify(obj)]
}

function buildHreflang(canonicalUrl: string): HeadConfig[] {
  return [
    ['link', {rel: 'alternate', hreflang: 'zh-CN', href: canonicalUrl}],
    ['link', {rel: 'alternate', hreflang: 'x-default', href: canonicalUrl}],
  ]
}

/* ── 主题关键词提取（从 title/description 启发式提取）──────────── */

function extractTopics(title: string, desc: string): {name: string}[] {
  const combined = `${title} ${desc}`
  const topics: {name: string}[] = []
  const kwMap: Record<string, string> = {
    '工业软件': '工业软件', '物联网': '物联网', 'AIoT': 'AIoT', 'AI': '人工智能',
    '智能体': '智能体', '云原生': '云原生', '微服务': '微服务', '安全': '物联网安全',
    '协议': '物联网协议', 'MQTT': 'MQTT协议', 'MCP': 'MCP协议', '边缘': '边缘计算',
    '数字孪生': '数字孪生', '智能制造': '智能制造', '智慧城市': '智慧城市',
    '车联网': '车联网', '农业': '农业物联网', '区块链': '区块链',
    '隐私计算': '隐私计算', '分布式身份': '分布式身份', 'DID': '去中心化身份',
    '传感器': '传感器技术', 'RFID': 'RFID', '通信': '通信技术',
    '平台': '物联网平台', '数据处理': '数据处理', '架构': '系统架构',
    'DCS': '工业控制系统', 'SCADA': 'SCADA', 'PLC': 'PLC',
  }
  for (const [key, name] of Object.entries(kwMap)) {
    if (combined.includes(key)) topics.push({'@type': 'Thing', name})
    if (topics.length >= 6) break
  }
  if (topics.length === 0) {
    topics.push({'@type': 'Thing', name: '物联网'}, {'@type': 'Thing', name: 'AIoT'})
  }
  return topics
}

/* ── JSON-LD 图 ──────────────────────────────────────────────────── */

function buildJsonLd(
  relativePath: string,
  canonicalUrl: string,
  title: string,
  description: string,
  dateModified?: string,
): HeadConfig[] {
  const bookId = `${SITE_URL}/#book`
  const authorId = `${SITE_URL}/#author`
  const websiteId = `${SITE_URL}/#website`
  const pageId = `${canonicalUrl}#webpage`
  const isAuthorPage = relativePath === 'preface/author.md'
  const isChapter = /\bchapter-\d+\b/.test(relativePath)

  /* ── 首页 ── */
  if (relativePath === 'index.md') {
    return [
      // Person 实体（作者）
      jsonLd({
        '@context': SCHEMA,
        '@type': 'Person',
        '@id': authorId,
        name: AUTHOR,
        url: `${SITE_URL}/preface/author`,
        sameAs: [
          'https://github.com/pnoker',
          'https://gitee.com/pnoker',
        ],
        description: 'IoT DC3 开源作者 · 架构师 · 物联网专家，十余年工业物联网平台研发经验。',
        knowsAbout: [
          {'@type': 'Thing', name: '物联网'},
          {'@type': 'Thing', name: '工业物联网'},
          {'@type': 'Thing', name: 'AIoT'},
          {'@type': 'Thing', name: '云原生'},
          {'@type': 'Thing', name: '智能体'},
        ],
      }),
      // WebSite + Sitelinks Searchbox
      jsonLd({
        '@context': SCHEMA,
        '@type': 'WebSite',
        '@id': websiteId,
        name: BOOK_TITLE,
        alternateName: 'IoT DC3 Book',
        url: `${SITE_URL}/`,
        description,
        inLanguage: 'zh-CN',
        publisher: {'@type': 'Person', '@id': authorId, name: AUTHOR},
        copyrightYear: 2025,
        potentialAction: {
          '@type': 'SearchAction',
          target: {
            '@type': 'EntryPoint',
            urlTemplate: `${SITE_URL}/search?q={search_term_string}`,
          },
          'query-input': 'required name=search_term_string',
        },
      }),
      // Book
      jsonLd({
        '@context': SCHEMA,
        '@type': 'Book',
        '@id': bookId,
        name: BOOK_TITLE,
        author: {'@type': 'Person', '@id': authorId, name: AUTHOR},
        description,
        abstract: BOOK_SUBTITLE,
        inLanguage: 'zh-CN',
        image: SITE_IMAGE,
        url: `${SITE_URL}/`,
        datePublished: BOOK_DATE_PUBLISHED,
        about: [
          {'@type': 'Thing', name: '物联网'},
          {'@type': 'Thing', name: '工业物联网'},
          {'@type': 'Thing', name: 'AIoT'},
          {'@type': 'Thing', name: '智能体'},
          {'@type': 'Thing', name: '云原生'},
        ],
        genre: ['计算机科学技术', '工业技术'],
        bookFormat: `${SCHEMA}/EBook`,
        isAccessibleForFree: true,
        publisher: {'@type': 'Person', name: AUTHOR},
        numberOfPages: 155,
      }),
    ]
  }

  /* ── 作者页：ProfilePage ── */
  if (isAuthorPage) {
    return [
      jsonLd({
        '@context': SCHEMA,
        '@type': 'ProfilePage',
        '@id': pageId,
        url: canonicalUrl,
        name: title,
        description,
        inLanguage: 'zh-CN',
        isPartOf: {'@type': 'WebSite', '@id': websiteId},
        breadcrumb: {
          '@type': 'BreadcrumbList',
          itemListElement: [
            {'@type': 'ListItem', position: 1, name: '首页', item: `${SITE_URL}/`},
            {'@type': 'ListItem', position: 2, name: '卷首', item: `${SITE_URL}/preface/`},
            {'@type': 'ListItem', position: 3, name: title, item: canonicalUrl},
          ],
        },
        mainEntity: {
          '@type': 'Person',
          '@id': authorId,
          name: AUTHOR,
          description: 'IoT DC3 开源作者 · 架构师 · 物联网专家',
          knowsAbout: [
            {'@type': 'Thing', name: '物联网'},
            {'@type': 'Thing', name: '工业物联网'},
            {'@type': 'Thing', name: 'AIoT'},
          ],
        },
      }),
    ]
  }

  /* ── 普通内页 + 章页 ── */
  const segment = relativePath.split('/')[0]
  const part = PART_BY_SEGMENT[segment]
  const topics = extractTopics(title, description)

  const itemListElement: object[] = [
    {'@type': 'ListItem', position: 1, name: '首页', item: `${SITE_URL}/`},
  ]
  if (part) {
    itemListElement.push({
      '@type': 'ListItem', position: 2, name: part.name, item: `${SITE_URL}${part.url}`,
    })
    itemListElement.push({
      '@type': 'ListItem', position: 3, name: title, item: canonicalUrl,
    })
  } else {
    itemListElement.push({
      '@type': 'ListItem', position: 2, name: title, item: canonicalUrl,
    })
  }

  // Article（所有内页都视为 Article）
  const articleLd: Record<string, unknown> = {
    '@context': SCHEMA,
    '@type': 'Article',
    '@id': pageId,
    headline: title,
    description,
    author: {'@type': 'Person', '@id': authorId, name: AUTHOR},
    inLanguage: 'zh-CN',
    url: canonicalUrl,
    image: SITE_IMAGE,
    isPartOf: {'@type': 'Book', '@id': bookId, name: BOOK_TITLE, url: `${SITE_URL}/`},
    datePublished: BOOK_DATE_PUBLISHED,
    about: topics,
    publisher: {'@type': 'Person', '@id': authorId, name: AUTHOR},
  }
  if (dateModified) {
    articleLd['dateModified'] = dateModified
  }

  const schemas: HeadConfig[] = [
    jsonLd(articleLd),
    jsonLd({
      '@context': SCHEMA,
      '@type': 'BreadcrumbList',
      '@id': `${canonicalUrl}#breadcrumb`,
      itemListElement,
    }),
  ]

  // 章页额外增强
  if (isChapter) {
    schemas.push(
      jsonLd({
        '@context': SCHEMA,
        '@type': 'SpeakableSpecification',
        cssSelector: ['.vp-doc h1', '.vp-doc h2'],
      }),
    )
    schemas.push(
      jsonLd({
        '@context': SCHEMA,
        '@type': 'WebPage',
        '@id': `${canonicalUrl}#webpage-article`,
        url: canonicalUrl,
        name: title,
        description,
        inLanguage: 'zh-CN',
        isPartOf: {'@type': 'WebSite', '@id': websiteId},
        breadcrumb: {'@id': `${canonicalUrl}#breadcrumb`},
        mainEntity: {'@type': 'Article', '@id': pageId},
        about: {'@type': 'Book', '@id': bookId, name: BOOK_TITLE},
      }),
    )
  }

  return schemas
}

/* ── 页面级 head 注入 ────────────────────────────────────────────── */

export function transformHead(context: TransformContext): HeadConfig[] {
  if (context.pageData.isNotFound) {
    return [
      ['meta', {name: 'robots', content: 'noindex,follow'}],
      ['meta', {name: 'description', content: '页面未找到 — 从工业软件到 AI 智能体'}],
      ['link', {rel: 'canonical', href: `${SITE_URL}/404`}],
    ]
  }

  const relativePath = context.pageData.relativePath
  const isHome = relativePath === 'index.md'
  const isChapter = /\bchapter-\d+\b/.test(relativePath)
  const title = context.pageData.title || context.title || BOOK_TITLE
  const fmDesc = context.pageData.frontmatter.description
  const description =
    typeof fmDesc === 'string' && fmDesc.trim() ? fmDesc.trim() : DEFAULT_DESCRIPTION
  const canonicalUrl = new URL(routeOf(relativePath), SITE_URL).href
  const dateModified: string | undefined = context.pageData.frontmatter.dateModified

  return [
    // ── 基础 SEO ──
    ['meta', {name: 'description', content: description}],
    ['meta', {name: 'robots', content: 'index,follow,max-image-preview:large,max-snippet:-1'}],
    ['meta', {name: 'author', content: AUTHOR}],
    ['link', {rel: 'canonical', href: canonicalUrl}],

    // ── hreflang ──
    ...buildHreflang(canonicalUrl),

    // ── Open Graph ──
    ['meta', {property: 'og:site_name', content: BOOK_TITLE}],
    ['meta', {property: 'og:type', content: isHome ? 'book' : 'article'}],
    ['meta', {property: 'og:title', content: title}],
    ['meta', {property: 'og:description', content: description}],
    ['meta', {property: 'og:url', content: canonicalUrl}],
    ['meta', {property: 'og:image', content: SITE_IMAGE}],
    ['meta', {property: 'og:image:width', content: String(SITE_IMAGE_WIDTH)}],
    ['meta', {property: 'og:image:height', content: String(SITE_IMAGE_HEIGHT)}],
    ['meta', {property: 'og:image:type', content: 'image/png'}],
    ['meta', {property: 'og:image:alt', content: `《${BOOK_TITLE}》封面`}],
    ['meta', {property: 'og:locale', content: 'zh_CN'}],

    // 章页 article 时间戳
    ...(isChapter
      ? ([
          ['meta', {property: 'article:author', content: AUTHOR}],
          ['meta', {property: 'article:published_time', content: BOOK_DATE_PUBLISHED}],
          ...(dateModified
            ? [['meta', {property: 'article:modified_time', content: dateModified}] as HeadConfig]
            : []),
          ['meta', {
            property: 'article:section',
            content: PART_BY_SEGMENT[relativePath.split('/')[0]]?.name || BOOK_TITLE,
          }],
        ] as HeadConfig[])
      : []),

    // ── Twitter Card ──
    ['meta', {name: 'twitter:card', content: 'summary_large_image'}],
    ['meta', {name: 'twitter:site', content: TWITTER_CREATOR}],
    ['meta', {name: 'twitter:creator', content: TWITTER_CREATOR}],
    ['meta', {name: 'twitter:title', content: title}],
    ['meta', {name: 'twitter:description', content: description}],
    ['meta', {name: 'twitter:image', content: SITE_IMAGE}],
    ['meta', {name: 'twitter:image:alt', content: `《${BOOK_TITLE}》封面`}],

    // ── JSON-LD ──
    ...buildJsonLd(relativePath, canonicalUrl, title, description, dateModified),
  ]
}
