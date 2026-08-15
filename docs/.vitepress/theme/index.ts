import type {Theme} from 'vitepress'
import {h, onMounted, watch, nextTick} from 'vue'
import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import {useRoute} from 'vitepress'
import './style.css'
import HeroWaves from './HeroWaves.vue'
import HeroParticles from './HeroParticles.vue'
import {coverBodyHtml} from './cover-art'

// 图库按钮 icon（四叶草：四片心形叶子绿色渐变 + 深绿茎，彩色 logo 风格）
const GALLERY_ICON =
  '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
  '<defs>' +
  '<linearGradient id="cloverLeaf" x1="0" y1="0" x2="1" y2="1">' +
  '<stop offset="0" stop-color="#4ADE80"></stop>' +
  '<stop offset="1" stop-color="#16A34A"></stop>' +
  '</linearGradient>' +
  '</defs>' +
  '<path d="M12 12 V21.5" stroke="#15803D" stroke-width="1.7" fill="none" stroke-linecap="round"></path>' +
  '<g transform="translate(12 12)" fill="url(#cloverLeaf)">' +
  '<path d="M0 0 C -2.6 -1.4 -4.6 -1.6 -5.2 -4.6 C -5.6 -6.4 -4 -7 -2.4 -6.4 C -1.2 -6 -0.6 -4.8 0 -3.6 C 0.6 -4.8 1.2 -6 2.4 -6.4 C 4 -7 5.6 -6.4 5.2 -4.6 C 4.6 -1.6 2.6 -1.4 0 0 Z"></path>' +
  '<path transform="rotate(90)" d="M0 0 C -2.6 -1.4 -4.6 -1.6 -5.2 -4.6 C -5.6 -6.4 -4 -7 -2.4 -6.4 C -1.2 -6 -0.6 -4.8 0 -3.6 C 0.6 -4.8 1.2 -6 2.4 -6.4 C 4 -7 5.6 -6.4 5.2 -4.6 C 4.6 -1.6 2.6 -1.4 0 0 Z"></path>' +
  '<path transform="rotate(180)" d="M0 0 C -2.6 -1.4 -4.6 -1.6 -5.2 -4.6 C -5.6 -6.4 -4 -7 -2.4 -6.4 C -1.2 -6 -0.6 -4.8 0 -3.6 C 0.6 -4.8 1.2 -6 2.4 -6.4 C 4 -7 5.6 -6.4 5.2 -4.6 C 4.6 -1.6 2.6 -1.4 0 0 Z"></path>' +
  '<path transform="rotate(270)" d="M0 0 C -2.6 -1.4 -4.6 -1.6 -5.2 -4.6 C -5.6 -6.4 -4 -7 -2.4 -6.4 C -1.2 -6 -0.6 -4.8 0 -3.6 C 0.6 -4.8 1.2 -6 2.4 -6.4 C 4 -7 5.6 -6.4 5.2 -4.6 C 4.6 -1.6 2.6 -1.4 0 0 Z"></path>' +
  '</g>' +
  '</svg>'

const theme: Theme = {
  extends: DefaultTheme,

  Layout() {
    return h(DefaultTheme.Layout, null, {
      // 首页 Hero 背景：粒子 + 波浪（保留 online 动效，仅首页）
      'home-hero-before': () => [h(HeroWaves), h(HeroParticles)],
      // 首页主视觉：内联封面（由 book/assets/cover.html 派生，颜色跟随明暗主题）
      'home-hero-image': () =>
        h('div', {class: 'hero-cover hero-logo'}, [
          h('div', {class: 'cover-body', innerHTML: coverBodyHtml}),
        ]),
      // header 搜索框前：全书插图图库入口
      'nav-bar-content-before': () =>
        h('a', {
          class: 'gallery-nav-link',
          href: '/figures',
          'aria-label': '全书插图',
          title: '全书插图',
        }, [
          h('span', {class: 'gallery-nav-icon', innerHTML: GALLERY_ICON}),
        ]),
    })
  },

  setup() {
    // 图表点击放大：绑定正文区图片，排除章/篇扉页（.no-zoom）；封面已内联为矢量，无需 zoom
    const route = useRoute()
    const initZoom = () =>
      nextTick(() => {
        mediumZoom('.vp-doc img:not(.no-zoom)', {
          background: 'var(--vp-c-bg)',
          margin: 24,
        })
      })
    // hero 按钮文字包成 span，实现「玻璃胶囊底 + 渐变色文字」双层结构（同 header 标题）
    const wrapButtons = () =>
      nextTick(() => {
        document.querySelectorAll('.VPButton:not([data-wrapped])').forEach((el) => {
          el.setAttribute('data-wrapped', '')
          const t = (el.textContent || '').trim()
          if (t) el.innerHTML = `<span class="vp-button-text">${t}</span>`
        })
      })
    // 章/篇扉页：内联渲染的固定 1240px 布局，按容器宽度动态缩放（写 CSS 变量，初始值在 CSS 里预置近似比例，避免 FOUC）
    const scaleDividers = () =>
      nextTick(() => {
        document.querySelectorAll('.divider-body').forEach((body) => {
          const page = body.querySelector<HTMLElement>('.page')
          if (!page) return
          const scale = body.clientWidth / 1240
          page.style.setProperty('--divider-scale', String(scale))
        })
      })
    // 首页封面：内联渲染的固定 794px 宽（A4），按容器宽度动态缩放
    const scaleCover = () =>
      nextTick(() => {
        document.querySelectorAll('.hero-cover').forEach((wrap) => {
          const body = wrap.querySelector<HTMLElement>('.cover-body')
          if (!body) return
          const scale = wrap.clientWidth / 794
          body.style.setProperty('--cover-scale', String(scale))
        })
      })
    onMounted(() => {
      initZoom()
      wrapButtons()
      scaleDividers()
      scaleCover()
    })
    watch(() => route.path, () => {
      initZoom()
      wrapButtons()
      scaleDividers()
      scaleCover()
    })
    // 窗口尺寸变化（响应式）时重新缩放扉页/封面
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', scaleDividers)
      window.addEventListener('resize', scaleCover)
    }
  },
}

export default theme
