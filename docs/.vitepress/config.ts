import {defineConfig} from 'vitepress'
import {sidebar} from './sidebar'
import {transformHead} from './seo'

const BOOK_TITLE = '从工业软件到 AI 智能体'

export default defineConfig({
  title: '从工业软件到 AI 智能体',
  description: 'AIoT 技术与实践 —— 从物联网平台到智能体应用',
  lang: 'zh-CN',
  base: '/',
  cleanUrls: true,
  srcExclude: ['design/**', 'AGENTS.md', 'CLAUDE.md'],

  sitemap: {hostname: 'https://book.dc3.site'},

  head: [
    // ── 插图主题变量（内联 SVG 颜色，跟随明暗主题）──
    ['link', {rel: 'stylesheet', href: '/figures.css'}],
    // ── 章/篇扉页主题样式（--div-* 变量，跟随明暗主题）──
    ['link', {rel: 'stylesheet', href: '/divider.css'}],

    // ── 资源预连接（性能：减少第三方域名 DNS/TLS 握手延迟）──
    ['link', {rel: 'preconnect', href: 'https://www.googletagmanager.com', crossorigin: 'anonymous'}],
    ['link', {rel: 'dns-prefetch', href: 'https://www.googletagmanager.com'}],
    ['link', {rel: 'preconnect', href: 'https://hm.baidu.com'}],
    ['link', {rel: 'dns-prefetch', href: 'https://hm.baidu.com'}],

    // ── 身份关联（IndieAuth / rel-me：搜索引擎整合作者身份）──
    ['link', {rel: 'me', href: 'https://github.com/pnoker'}],

    // ── Feed 自动发现 ──
    ['link', {rel: 'alternate', type: 'application/atom+xml', title: BOOK_TITLE, href: '/feed.xml'}],

    // ── 图标与主题 ──
    ['link', {rel: 'icon', type: 'image/svg+xml', href: '/logo.svg'}],
    ['meta', {name: 'theme-color', content: '#1296db'}],

    ['meta', {
      name: 'keywords',
      content: 'AIoT,物联网,工业物联网,智能体,IoT DC3,云原生,从工业软件到AI智能体,在线电子书',
    }],

    // ── 分析 ──
    ['script', {async: true, src: 'https://www.googletagmanager.com/gtag/js?id=G-VVTDCS4KSE'}],
    ['script', {}, 'window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag("js",new Date());gtag("config","G-VVTDCS4KSE");'],
    ['script', {}, 'var _hmt=_hmt||[];'],
    ['script', {async: true, src: 'https://hm.baidu.com/hm.js?6474f729cc0afe2083c201a7a0e0c60e'}],

    // 搜索引擎验证标签 — 在对应平台（Search Console / 百度站长 / Bing Webmaster）完成
    // 所有权验证后，取消注释并填入验证值。Google 和百度可通过 DNS TXT 记录替代此 meta 方式。
    // ['meta', {name: 'google-site-verification', content: '你的验证值'}],
    // ['meta', {name: 'baidu-site-verification', content: '你的验证值'}],
    // ['meta', {name: 'msvalidate.01', content: '你的验证值'}],
  ],

  transformHead,

  markdown: {
    config(md: any) {
      md.core.ruler.before('inline', 'cn_bold_close', (state: any) => {
        for (const tok of state.tokens) {
          if (tok.type === 'inline' && tok.content) {
            tok.content = tok.content.replace(
              /\*\*([^*\n]+?[，。、；：？！）】」』》〈〕])\*\*(?=\S)/g,
              '<strong>$1</strong>'
            )
          }
        }
      })
    },
  },

  themeConfig: {
    logo: '/logo.svg',
    siteTitle: '从工业软件到 AI 智能体',
    outline: {level: [2, 3], label: '本页目录'},
    sidebar,

    search: {
      provider: 'local',
      options: {
        translations: {
          button: {buttonText: '搜索全书', buttonAriaLabel: '搜索'},
          modal: {
            noResultsText: '无法找到结果',
            resetButtonTitle: '清除查询',
            footer: {selectText: '选择', navigateText: '切换', closeText: '关闭'},
          },
        },
      },
    },

    socialLinks: [
      {icon: 'github', link: 'https://github.com/pnoker/iot-dc3'},
      {icon: 'gitee', link: 'https://gitee.com/pnoker/iot-dc3'},
    ],

    footer: {
      message: '从工业软件到 AI 智能体 · 构建面向智能场景演进的多协议、云原生、AI Native 工业物联网平台',
      copyright: '张红元 著 · © 2016–2026',
    },

    docFooter: {prev: '上一章', next: '下一章'},
    darkModeSwitchLabel: '主题',
    sidebarMenuLabel: '目录',
    returnToTopLabel: '回到顶部',
    outlineTitle: '本页目录',
    langMenuLabel: '语言',
  },
})
