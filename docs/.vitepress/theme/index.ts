import type {Theme} from 'vitepress'
import {h, onMounted, watch, nextTick} from 'vue'
import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import {useRoute} from 'vitepress'
import './style.css'
import BookCover from './BookCover.vue'
import HeroWaves from './HeroWaves.vue'
import HeroParticles from './HeroParticles.vue'

const theme: Theme = {
  extends: DefaultTheme,

  Layout() {
    return h(DefaultTheme.Layout, null, {
      // 首页 Hero 背景：粒子 + 波浪（保留 online 动效，仅首页）
      'home-hero-before': () => [h(HeroWaves), h(HeroParticles)],
      // 首页主视觉：立体书封（hero-logo class 让粒子向书封聚拢）
      'home-hero-image': () =>
        h('div', {class: 'hero-book-cover hero-logo'}, [h(BookCover, {english: false})]),
    })
  },

  setup() {
    // 图表点击放大：绑定正文区图片，排除章/篇扉页（.no-zoom）
    const route = useRoute()
    const initZoom = () =>
      nextTick(() => {
        mediumZoom('.vp-doc img:not(.no-zoom)', {
          background: 'var(--vp-c-bg)',
          margin: 24,
        })
      })
    onMounted(initZoom)
    watch(() => route.path, initZoom)
  },
}

export default theme
