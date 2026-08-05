import {defineConfig} from 'vitepress'
import {sidebar} from './sidebar'
import {transformHead} from './seo'

export default defineConfig({
  title: '从工业软件到 AI 智能体',
  description: 'AIoT 技术与实践 —— 从物联网平台到智能体应用',
  lang: 'zh-CN',
  base: '/',
  cleanUrls: true,
  srcExclude: ['design/**', 'AGENTS.md', 'CLAUDE.md'],

  sitemap: {hostname: 'https://book.dc3.site'},

  head: [
    ['link', {rel: 'icon', type: 'image/svg+xml', href: '/logo.svg'}],
    ['meta', {name: 'theme-color', content: '#1296db'}],
    ['meta', {
      name: 'keywords',
      content: 'AIoT,物联网,工业物联网,智能体,IoT DC3,云原生,从工业软件到AI智能体,在线电子书',
    }],
  ],

  transformHead,

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
      {icon: 'github', link: 'https://github.com/pnoker/iot-dc3-book'},
    ],

    docFooter: {prev: '上一章', next: '下一章'},
    darkModeSwitchLabel: '主题',
    sidebarMenuLabel: '目录',
    returnToTopLabel: '回到顶部',
    outlineTitle: '本页目录',
    langMenuLabel: '语言',
  },
})
