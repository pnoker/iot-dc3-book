import type {Theme} from 'vitepress'
import {h, onMounted, watch, nextTick} from 'vue'
import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import {useRoute} from 'vitepress'
import './style.css'
import HeroWaves from './HeroWaves.vue'
import HeroParticles from './HeroParticles.vue'

const theme: Theme = {
  extends: DefaultTheme,

  Layout() {
    return h(DefaultTheme.Layout, null, {
      // 首页 Hero 背景：粒子 + 波浪（保留 online 动效，仅首页）
      'home-hero-before': () => [h(HeroWaves), h(HeroParticles)],
      // 首页主视觉：真实封面图（hero-logo class 让粒子向封面聚拢）
      'home-hero-image': () =>
        h('img', {
          class: 'hero-cover-image hero-logo',
          src: '/cover.png',
          alt: '《从工业软件到 AI 智能体》封面',
        }),
    })
  },

  setup() {
    // 图表点击放大：绑定正文区图片，排除章/篇扉页（.no-zoom）
    const route = useRoute()
    const initZoom = () =>
      nextTick(() => {
        mediumZoom('.vp-doc img:not(.no-zoom), .hero-cover-image', {
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
    onMounted(() => {
      initZoom()
      wrapButtons()
    })
    watch(() => route.path, () => {
      initZoom()
      wrapButtons()
    })
  },
}

export default theme
