import type {HeadConfig, TransformContext} from 'vitepress'

const SITE_URL = 'https://book.dc3.site'
const SITE_IMAGE = `${SITE_URL}/cover.png`
const SITE_IMAGE_WIDTH = 2479
const SITE_IMAGE_HEIGHT = 3508
// 社交卡片用横版 OG 图（1200×630），Book/Article 结构化数据仍用竖版封面 SITE_IMAGE
const OG_IMAGE = `${SITE_URL}/og-image.png`
const OG_IMAGE_WIDTH = 1200
const OG_IMAGE_HEIGHT = 630
const BOOK_TITLE = '从工业软件到 AI 智能体'
const BOOK_TITLE_EN = 'From Industrial Software to AI Agents'
const BOOK_SUBTITLE = '构建面向智能体演进的多协议、云原生、开源工业物联网平台'
const BOOK_SUBTITLE_EN = 'Building a multi-protocol, cloud-native, open-source industrial IoT platform ready to evolve toward AI agents'
const AUTHOR = '张红元'
const TWITTER_CREATOR = '@iotdc3'
const BOOK_DATE_PUBLISHED = '2025-06-01'
const COPYRIGHT_HOLDER = '张红元'
const LICENSE_URL = `${SITE_URL}/copyright`
const LICENSE_URL_EN = `${SITE_URL}/en/copyright`
const DEFAULT_DESCRIPTION =
  '《从工业软件到 AI 智能体》—— AIoT 技术与实践，从物联网平台到智能体应用。作者张红元，14 章 · 200 张架构图，IoT DC3 开源贯穿全书。'
const DEFAULT_DESCRIPTION_EN =
  'From Industrial Software to AI Agents — AIoT technology and practice, from IoT platform to agent applications. By Zhang Hongyuan, 14 chapters, 200+ architecture diagrams, with open-source IoT DC3 throughout.'

const SCHEMA = 'https://schema.org'

const PART_BY_SEGMENT: Record<string, {name: string; nameEn: string; url: string}> = {
  preface: {name: '卷首', nameEn: 'Front Matter', url: '/preface/'},
  foundations: {name: '基础篇', nameEn: 'Part I · Foundations', url: '/foundations/'},
  technical: {name: '技术篇', nameEn: 'Part II · Technology', url: '/technical/'},
  applications: {name: '应用篇', nameEn: 'Part III · Applications', url: '/applications/'},
  appendix: {name: '附录', nameEn: 'Appendix', url: '/appendix/'},
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

function buildHreflang(canonicalUrl: string, enUrl?: string, zhUrl?: string): HeadConfig[] {
  // 英文页同时声明 en 与 zh-CN 互链（中文版结构必然存在）；中文页暂不声明 en 互链（翻译未完成）
  if (enUrl && zhUrl) {
    return [
      ['link', {rel: 'alternate', hreflang: 'en', href: enUrl}],
      ['link', {rel: 'alternate', hreflang: 'zh-CN', href: zhUrl}],
      ['link', {rel: 'alternate', hreflang: 'x-default', href: zhUrl}],
    ]
  }
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

const PERSON_DESC_EN =
  'Creator of the open-source IoT DC3 platform · architect · IoT specialist with over a decade of industrial IoT platform engineering.'

function buildJsonLd(
  relativePath: string,
  canonicalUrl: string,
  title: string,
  description: string,
  dateModified?: string,
  lang: 'zh-CN' | 'en' = 'zh-CN',
): HeadConfig[] {
  const isEn = lang === 'en'
  const bookTitle = isEn ? BOOK_TITLE_EN : BOOK_TITLE
  const bookSubtitle = isEn ? BOOK_SUBTITLE_EN : BOOK_SUBTITLE
  const licenseUrl = isEn ? LICENSE_URL_EN : LICENSE_URL
  const homeLabel = isEn ? 'Home' : '首页'
  const bookId = `${SITE_URL}/#book`
  const authorId = `${SITE_URL}/#author`
  const websiteId = `${SITE_URL}/#website`
  const pageId = `${canonicalUrl}#webpage`
  const isAuthorPage = relativePath === 'preface/author.md' || relativePath === 'en/preface/author.md'
  const isChapter = /\bchapter-\d+\b/.test(relativePath)

  /* ── 首页 ── */
  if (relativePath === 'index.md' || relativePath === 'en/index.md') {
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
        description: isEn ? PERSON_DESC_EN : 'IoT DC3 开源作者 · 架构师 · 物联网专家，十余年工业物联网平台研发经验。',
        knowsAbout: isEn
          ? [
              {'@type': 'Thing', name: 'Internet of Things'},
              {'@type': 'Thing', name: 'Industrial IoT'},
              {'@type': 'Thing', name: 'AIoT'},
              {'@type': 'Thing', name: 'Cloud Native'},
              {'@type': 'Thing', name: 'AI Agents'},
            ]
          : [
              {'@type': 'Thing', name: '物联网'},
              {'@type': 'Thing', name: '工业物联网'},
              {'@type': 'Thing', name: 'AIoT'},
              {'@type': 'Thing', name: '云原生'},
              {'@type': 'Thing', name: '智能体'},
            ],
      }),
      // WebSite（站内搜索无独立 URL 入口，无法提供 Sitelinks Searchbox，故不声明 potentialAction）
      jsonLd({
        '@context': SCHEMA,
        '@type': 'WebSite',
        '@id': websiteId,
        name: bookTitle,
        alternateName: 'IoT DC3 Book',
        url: `${SITE_URL}/`,
        description,
        inLanguage: lang,
        publisher: {'@type': 'Person', '@id': authorId, name: AUTHOR},
        copyrightYear: 2025,
      }),
      // Book
      jsonLd({
        '@context': SCHEMA,
        '@type': 'Book',
        '@id': bookId,
        name: bookTitle,
        author: {'@type': 'Person', '@id': authorId, name: AUTHOR},
        description,
        abstract: bookSubtitle,
        inLanguage: lang,
        image: SITE_IMAGE,
        url: `${SITE_URL}/`,
        datePublished: BOOK_DATE_PUBLISHED,
        about: isEn
          ? [
              {'@type': 'Thing', name: 'Internet of Things'},
              {'@type': 'Thing', name: 'Industrial IoT'},
              {'@type': 'Thing', name: 'AIoT'},
              {'@type': 'Thing', name: 'AI Agents'},
              {'@type': 'Thing', name: 'Cloud Native'},
            ]
          : [
              {'@type': 'Thing', name: '物联网'},
              {'@type': 'Thing', name: '工业物联网'},
              {'@type': 'Thing', name: 'AIoT'},
              {'@type': 'Thing', name: '智能体'},
              {'@type': 'Thing', name: '云原生'},
            ],
        genre: isEn ? ['Computer Science', 'Industrial Technology'] : ['计算机科学技术', '工业技术'],
        bookFormat: `${SCHEMA}/EBook`,
        isAccessibleForFree: true,
        publisher: {'@type': 'Person', name: AUTHOR},
        copyrightHolder: {'@type': 'Person', name: COPYRIGHT_HOLDER},
        copyrightYear: 2025,
        license: licenseUrl,
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
        inLanguage: lang,
        isPartOf: {'@type': 'WebSite', '@id': websiteId},
        breadcrumb: {
          '@type': 'BreadcrumbList',
          itemListElement: [
            {'@type': 'ListItem', position: 1, name: homeLabel, item: `${SITE_URL}/`},
            {'@type': 'ListItem', position: 2, name: isEn ? 'Front Matter' : '卷首', item: `${SITE_URL}/preface/`},
            {'@type': 'ListItem', position: 3, name: title, item: canonicalUrl},
          ],
        },
        mainEntity: {
          '@type': 'Person',
          '@id': authorId,
          name: AUTHOR,
          description: isEn ? PERSON_DESC_EN : 'IoT DC3 开源作者 · 架构师 · 物联网专家',
          knowsAbout: isEn
            ? [
                {'@type': 'Thing', name: 'Internet of Things'},
                {'@type': 'Thing', name: 'Industrial IoT'},
                {'@type': 'Thing', name: 'AIoT'},
              ]
            : [
                {'@type': 'Thing', name: '物联网'},
                {'@type': 'Thing', name: '工业物联网'},
                {'@type': 'Thing', name: 'AIoT'},
              ],
        },
      }),
    ]
  }

  /* ── 普通内页 + 章页 ── */
  const segment = relativePath.replace(/^en\//, '').split('/')[0]
  const part = PART_BY_SEGMENT[segment]
  const topics = extractTopics(title, description)

  const itemListElement: object[] = [
    {'@type': 'ListItem', position: 1, name: homeLabel, item: `${SITE_URL}/`},
  ]
  if (part) {
    itemListElement.push({
      '@type': 'ListItem', position: 2, name: isEn ? part.nameEn : part.name, item: `${SITE_URL}${part.url}`,
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
    inLanguage: lang,
    url: canonicalUrl,
    image: SITE_IMAGE,
    isPartOf: {'@type': 'Book', '@id': bookId, name: bookTitle, url: `${SITE_URL}/`},
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
        inLanguage: lang,
        isPartOf: {'@type': 'WebSite', '@id': websiteId},
        breadcrumb: {'@id': `${canonicalUrl}#breadcrumb`},
        mainEntity: {'@type': 'Article', '@id': pageId},
        about: {'@type': 'Book', '@id': bookId, name: bookTitle},
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
  const isEn = relativePath === 'en/index.md' || relativePath.startsWith('en/')
  const lang: 'zh-CN' | 'en' = isEn ? 'en' : 'zh-CN'
  const isHome = relativePath === 'index.md' || relativePath === 'en/index.md'
  const isChapter = /\bchapter-\d+\b/.test(relativePath)
  const title = context.pageData.title || context.title || (isEn ? BOOK_TITLE_EN : BOOK_TITLE)
  const fmDesc = context.pageData.frontmatter.description
  const description =
    typeof fmDesc === 'string' && fmDesc.trim() ? fmDesc.trim() : (isEn ? DEFAULT_DESCRIPTION_EN : DEFAULT_DESCRIPTION)
  const canonicalUrl = new URL(routeOf(relativePath), SITE_URL).href
  const dateModified: string | undefined = context.pageData.frontmatter.dateModified
  // keywords 按语言注入（此前在 config head 全局配中文，英文页会带中文关键词）
  const keywords = isEn
    ? 'AIoT,Industrial IoT,internet of things,AI agents,IoT DC3,cloud-native,From Industrial Software to AI Agents,online book'
    : 'AIoT,物联网,工业物联网,智能体,IoT DC3,云原生,从工业软件到AI智能体,在线电子书'
  // 英文页的中文对照路径（/en/foundations/... → /foundations/...，翻译镜像结构必然存在）
  const zhCounterpartUrl = isEn
    ? new URL(routeOf(relativePath.replace(/^en\//, '')), SITE_URL).href
    : undefined

  return [
    // ── 基础 SEO ──
    ['meta', {name: 'description', content: description}],
    ['meta', {name: 'robots', content: 'index,follow,max-image-preview:large,max-snippet:-1'}],
    ['meta', {name: 'author', content: AUTHOR}],
    ['link', {rel: 'canonical', href: canonicalUrl}],

    // ── AEO: 向 AI 答案引擎声明机器可读摘要与全量正文 ──
    ['link', {rel: 'alternate', type: 'text/plain', href: `${SITE_URL}/llms.txt`, title: 'AI-readable site summary'}],
    ['link', {rel: 'alternate', type: 'text/plain', href: `${SITE_URL}/llms-full.txt`, title: 'AI-readable full content'}],

    // ── hreflang ──
    ...buildHreflang(canonicalUrl, isEn ? canonicalUrl : undefined, zhCounterpartUrl),

    // ── Open Graph ──
    ['meta', {property: 'og:site_name', content: isEn ? BOOK_TITLE_EN : BOOK_TITLE}],
    ['meta', {property: 'og:type', content: isHome ? 'book' : 'article'}],
    ['meta', {property: 'og:title', content: title}],
    ['meta', {property: 'og:description', content: description}],
    ['meta', {property: 'og:url', content: canonicalUrl}],
    ['meta', {property: 'og:image', content: OG_IMAGE}],
    ['meta', {property: 'og:image:width', content: String(OG_IMAGE_WIDTH)}],
    ['meta', {property: 'og:image:height', content: String(OG_IMAGE_HEIGHT)}],
    ['meta', {property: 'og:image:type', content: 'image/png'}],
    ['meta', {property: 'og:image:alt', content: isEn ? `${BOOK_TITLE_EN} · by Zhang Hongyuan · AIoT technology and practice` : `${BOOK_TITLE} · ${AUTHOR} 著 · AIoT 技术与实践`}],
    ['meta', {property: 'og:locale', content: isEn ? 'en_US' : 'zh_CN'}],

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
            content: (isEn ? PART_BY_SEGMENT[relativePath.replace(/^en\//, '').split('/')[0]]?.nameEn : PART_BY_SEGMENT[relativePath.split('/')[0]]?.name) || (isEn ? BOOK_TITLE_EN : BOOK_TITLE),
          }],
        ] as HeadConfig[])
      : []),

    // ── Twitter Card ──
    ['meta', {name: 'twitter:card', content: 'summary_large_image'}],
    ['meta', {name: 'twitter:site', content: TWITTER_CREATOR}],
    ['meta', {name: 'twitter:creator', content: TWITTER_CREATOR}],
    ['meta', {name: 'twitter:title', content: title}],
    ['meta', {name: 'twitter:description', content: description}],
    ['meta', {name: 'twitter:image', content: OG_IMAGE}],
    ['meta', {name: 'twitter:image:alt', content: isEn ? `${BOOK_TITLE_EN} · by Zhang Hongyuan · AIoT technology and practice` : `${BOOK_TITLE} · ${AUTHOR} 著 · AIoT 技术与实践`}],
    ['meta', {name: 'keywords', content: keywords}],

    // ── JSON-LD ──
    ...buildJsonLd(relativePath, canonicalUrl, title, description, dateModified, lang),
  ]
}
