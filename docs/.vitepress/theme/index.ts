import type {Theme} from 'vitepress'
import {h, onMounted, watch, nextTick} from 'vue'
import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import {useRoute} from 'vitepress'
import './style.css'
import HeroWaves from './HeroWaves.vue'
import HeroParticles from './HeroParticles.vue'
import {coverBodyHtml} from './cover-art'

// 图库按钮 icon（四叶草：iconfont 原版四层绿色，茎/外叶/内叶/中心，主题协同）
const GALLERY_ICON =
  '<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
  '<path d="M512.776 587.284s-7.744 193.284-68 304" fill="var(--clover-stem)"></path>' +
  '<path d="M792.776 159.284s112 46.856 112 112c0 65.14-118.22 195.428-392 192 0 0-31.344-91.256 0-212 32.692-125.928 97.632-199.864 160-208 50.08-6.532 66.688 32.392 120 116z" fill="var(--clover-leaf-1)"></path>' +
  '<path d="M511.536 459.276c-5.508-18.824-26.26-102.06 1.24-207.992 32.692-125.928 97.632-199.864 160-208 50.08-6.532 66.688 32.392 120 116l0.04 0.016-281.28 299.976z" fill="var(--clover-leaf-2)"></path>' +
  '<path d="M791.396 720.032s-46.98 111.948-112.124 111.876c-65.14-0.068-195.3-118.428-191.576-392.204 0 0 91.288-31.248 212 0.228 125.892 32.824 199.76 97.844 207.828 160.224 6.476 50.084-32.464 66.652-116.128 119.876z" fill="var(--clover-leaf-1)"></path>' +
  '<path d="M491.704 438.468c18.832-5.488 102.088-26.152 207.992 1.464 125.892 32.824 199.76 97.844 207.828 160.224 6.476 50.084-32.464 66.652-116.128 119.876l-0.016 0.036-299.676-281.6z" fill="var(--clover-leaf-2)"></path>' +
  '<path d="M230.648 718.044s-111.9-47.1-111.76-112.24c0.14-65.144 118.644-195.176 392.416-191.156 0 0 31.148 91.32-0.46 212-32.96 125.856-98.056 199.652-160.444 207.656-50.092 6.424-66.62-32.536-119.752-116.26z" fill="var(--clover-leaf-1)"></path>' +
  '<path d="M230.612 718.028l281.924-299.372c5.464 18.84 26.04 102.116-1.692 207.992-32.96 125.856-98.056 199.652-160.444 207.656-50.092 6.424-66.62-32.536-119.752-116.26l-0.036-0.016z" fill="var(--clover-leaf-2)"></path>' +
  '<path d="M233.24 157.3S280.46 45.452 345.6 45.664c65.14 0.208 195.048 118.852 190.732 392.616 0 0-91.352 31.052-212-0.684-125.82-33.096-199.548-98.272-207.48-160.672-6.372-50.096 32.604-66.58 116.388-119.624z" fill="var(--clover-leaf-1)"></path>' +
  '<path d="M532.324 439.508c-18.844 5.448-102.144 25.932-207.992-1.912-125.82-33.096-199.548-98.272-207.48-160.672-6.372-50.096 32.604-66.58 116.388-119.624l0.016-0.036 299.068 282.244z" fill="var(--clover-leaf-2)"></path>' +
  '<path d="M640.944 315.064l-83.996 118.844 80.044 121.54-118.844-83.992-121.536 80.044 83.992-118.844-80.044-121.54 118.844 83.992 121.54-80.044z" fill="var(--clover-center)"></path>' +
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
