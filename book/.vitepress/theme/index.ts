import type {Theme} from 'vitepress'
import {h, onBeforeUnmount, onMounted, watch, nextTick} from 'vue'
import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import {useRoute} from 'vitepress'
import './style.css'
import './immersive-header.css'
import HeroWaves from './HeroWaves.vue'
import BookHome from './BookHome.vue'
import FooterSignal from './FooterSignal.vue'
import {coverBodyHtml, coverBodyHtmlEn} from './cover-art'
import {useImmersiveHeader} from './useImmersiveHeader'

function tiltHeroBook(event: PointerEvent) {
  if (event.pointerType === 'touch') return
  const shell = event.currentTarget
  if (!(shell instanceof HTMLElement)) return
  const rect = shell.getBoundingClientRect()
  const x = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width))
  const y = Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height))
  shell.style.setProperty('--hero-book-rotate-x', `${(2.4 - y * 4).toFixed(2)}deg`)
  shell.style.setProperty('--hero-book-rotate-y', `${(-6.5 + x * 4.5).toFixed(2)}deg`)
  shell.style.setProperty('--hero-pointer-x', `${(x * 100).toFixed(1)}%`)
  shell.style.setProperty('--hero-pointer-y', `${(y * 100).toFixed(1)}%`)
}

function resetHeroBook(event: PointerEvent) {
  const shell = event.currentTarget
  if (!(shell instanceof HTMLElement)) return
  shell.style.removeProperty('--hero-book-rotate-x')
  shell.style.removeProperty('--hero-book-rotate-y')
  shell.style.removeProperty('--hero-pointer-x')
  shell.style.removeProperty('--hero-pointer-y')
}

const theme: Theme = {
  extends: DefaultTheme,

  enhanceApp({app}) {
    app.component('BookHome', BookHome)
  },

  Layout() {
    const route = useRoute()
    const homeLayout = route.path === '/' || route.path === '/en' || route.path === '/en/'
    return h(DefaultTheme.Layout, {class: {'dc3-book-home-layout': homeLayout}}, {
      // 与 online 首页同源的单画布力场：网格挤压、粒子网络和悬浮点阵 Logo
      'home-hero-before': () => h(HeroWaves),
      // 首页主视觉：内联封面（由 book/assets/cover.html 派生，颜色跟随明暗主题）
      'home-hero-image': () =>
        h('div', {
          class: 'hero-cover-shell hero-logo',
          'aria-hidden': 'true',
          onPointermove: tiltHeroBook,
          onPointerleave: resetHeroBook,
        }, [
          h('div', {class: 'hero-book'}, [
            h('div', {class: 'hero-book-back'}),
            h('div', {class: 'hero-book-pages'}),
            h('div', {class: 'hero-cover'}, [
              h('div', {
                class: 'cover-body',
                innerHTML: route.path === '/en' || route.path.startsWith('/en/') ? coverBodyHtmlEn : coverBodyHtml,
              }),
            ]),
            h('div', {class: 'hero-book-spine'}),
          ]),
        ]),
      'layout-bottom': () => h(FooterSignal),
    })
  },

  setup() {
    // 图表点击放大：绑定正文区图片，排除章/篇扉页（.no-zoom）；封面已内联为矢量，无需 zoom
    const route = useRoute()
    let currentYearTimer = 0
    useImmersiveHeader()
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
    // 构建产物提供年份回退；浏览器再按访客本地时间校正，跨年未重新部署也不会停在旧年份。
    const syncCurrentYear = () =>
      nextTick(() => {
        const year = String(new Date().getFullYear())
        document.querySelectorAll<HTMLElement>('[data-current-year]').forEach((el) => {
          el.textContent = year
          el.setAttribute('datetime', year)
        })
      })
    // 四叶草图库入口已并入社交图标组：VPSocialLink 默认 target=_blank，
    // 剥离内部链接的 target/rel，让 /figures 走站内 SPA 路由（外链不受影响）
    const fixInternalSocialLinks = () =>
      nextTick(() => {
        document.querySelectorAll<HTMLAnchorElement>('.VPSocialLink[href^="/"]').forEach((a) => {
          a.removeAttribute('target')
          a.removeAttribute('rel')
        })
      })
    const closeScreenAfterMobileAppearance = (event: MouseEvent) => {
      const target = event.target
      if (!(target instanceof Element)) return
      if (!target.closest('.VPNavScreenAppearance .VPSwitchAppearance')) return
      window.setTimeout(() => {
        if (!document.querySelector('#VPNavScreen')) return
        document.querySelector<HTMLButtonElement>('.VPNavBarHamburger')?.click()
      }, 0)
    }
    onMounted(() => {
      initZoom()
      wrapButtons()
      scaleDividers()
      scaleCover()
      syncCurrentYear()
      fixInternalSocialLinks()
      currentYearTimer = window.setInterval(syncCurrentYear, 60 * 60 * 1000)
      document.addEventListener('click', closeScreenAfterMobileAppearance)
      // 抽屉/extra 菜单按需渲染，挂载后再出现的社交链接也要剥离 target
      const observer = new MutationObserver(() => {
        fixInternalSocialLinks()
      })
      observer.observe(document.body, {childList: true, subtree: true})
    })
    onBeforeUnmount(() => {
      document.removeEventListener('click', closeScreenAfterMobileAppearance)
      window.clearInterval(currentYearTimer)
    })
    watch(() => route.path, () => {
      initZoom()
      wrapButtons()
      scaleDividers()
      scaleCover()
      syncCurrentYear()
      fixInternalSocialLinks()
    })
    // 窗口尺寸变化（响应式）时重新缩放扉页/封面
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', scaleDividers)
      window.addEventListener('resize', scaleCover)
    }
  },
}

export default theme
