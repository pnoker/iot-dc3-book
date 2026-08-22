import type {Theme} from 'vitepress'
import {h, onBeforeUnmount, onMounted, watch, nextTick} from 'vue'
import DefaultTheme from 'vitepress/theme'
import mediumZoom from 'medium-zoom'
import {useRoute, useRouter} from 'vitepress'
import './style.css'
import HeroWaves from './HeroWaves.vue'
import HeroParticles from './HeroParticles.vue'
import {coverBodyHtml, coverBodyHtmlEn} from './cover-art'

const theme: Theme = {
  extends: DefaultTheme,

  Layout() {
    const route = useRoute()
    return h(DefaultTheme.Layout, null, {
      // 首页 Hero 背景：粒子 + 波浪（保留 online 动效，仅首页）
      'home-hero-before': () => [h(HeroWaves), h(HeroParticles)],
      // 首页主视觉：内联封面（由 book/assets/cover.html 派生，颜色跟随明暗主题）
      'home-hero-image': () =>
        h('div', {class: 'hero-cover hero-logo'}, [
          h('div', {
            class: 'cover-body',
            innerHTML: route.path === '/en' || route.path.startsWith('/en/') ? coverBodyHtmlEn : coverBodyHtml,
          }),
        ]),
    })
  },

  setup() {
    // 图表点击放大：绑定正文区图片，排除章/篇扉页（.no-zoom）；封面已内联为矢量，无需 zoom
    const route = useRoute()
    const router = useRouter()
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
    // 四叶草图库入口已并入社交图标组：VPSocialLink 默认 target=_blank，
    // 剥离内部链接的 target/rel，让 /figures 走站内 SPA 路由（外链不受影响）
    const fixInternalSocialLinks = () =>
      nextTick(() => {
        document.querySelectorAll<HTMLAnchorElement>('.VPSocialLink[href^="/"]').forEach((a) => {
          a.removeAttribute('target')
          a.removeAttribute('rel')
        })
      })
    const enhanceMobileLanguageControl = () =>
      nextTick(() => {
        document.querySelectorAll<HTMLElement>('.VPNavScreenTranslations').forEach((container) => {
          if (container.querySelector('.dc3-mobile-language-control')) return
          const title = container.querySelector<HTMLButtonElement>('.title')
          const link = container.querySelector<HTMLAnchorElement>('.list .link')
          const href = link?.getAttribute('href')
          if (!title || !link || !href) return

          const currentIsEnglish = route.path === '/en' || route.path.startsWith('/en/')
          const languageControl = document.createElement('div')
          languageControl.className = 'dc3-mobile-language-control'
          const languageLabel = document.createElement('span')
          languageLabel.className = 'dc3-mobile-language-label'
          languageLabel.textContent = currentIsEnglish ? 'Language' : '语言'
          const languageIcon = document.createElement('span')
          languageIcon.className = 'vpi-languages dc3-mobile-language-icon'
          languageLabel.prepend(languageIcon)

          const segmented = document.createElement('div')
          segmented.className = 'dc3-mobile-language-segmented'
          segmented.setAttribute('role', 'group')
          segmented.setAttribute('aria-label', currentIsEnglish ? 'Language' : '语言')
          const currentSegment = document.createElement('button')
          currentSegment.type = 'button'
          currentSegment.className = 'dc3-mobile-language-segment active'
          currentSegment.setAttribute('aria-pressed', 'true')
          currentSegment.textContent = currentIsEnglish ? 'English' : '中文'
          const targetSegment = document.createElement('button')
          targetSegment.type = 'button'
          targetSegment.className = 'dc3-mobile-language-segment'
          targetSegment.setAttribute('aria-pressed', 'false')
          targetSegment.dataset.href = href
          targetSegment.textContent = currentIsEnglish ? '中文' : 'English'

          segmented.append(currentSegment, targetSegment)
          languageControl.append(languageLabel, segmented)
          title.hidden = true
          const list = container.querySelector<HTMLElement>('.list')
          if (list) list.hidden = true
          container.classList.add('dc3-mobile-language-ready')
          container.append(languageControl)
        })
      })
    const handleMobileLanguageClick = (event: MouseEvent) => {
      const target = event.target
      if (!(target instanceof Element)) return
      const segment = target.closest<HTMLButtonElement>('.dc3-mobile-language-segment')
      if (segment) {
        const href = segment.dataset.href
        if (!href) return
        event.preventDefault()
        event.stopImmediatePropagation()
        void router.go(href)
        return
      }
      const title = target.closest<HTMLButtonElement>('.VPNavScreenTranslations .title')
      if (!title) return
      const href = title.parentElement
        ?.querySelector<HTMLAnchorElement>('.list .link')
        ?.getAttribute('href')
      if (!href) return
      event.preventDefault()
      event.stopImmediatePropagation()
      void router.go(href)
    }
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
      fixInternalSocialLinks()
      enhanceMobileLanguageControl()
      document.addEventListener('click', handleMobileLanguageClick, true)
      document.addEventListener('click', closeScreenAfterMobileAppearance)
      // 抽屉/extra 菜单按需渲染，挂载后再出现的社交链接也要剥离 target
      const observer = new MutationObserver(() => {
        fixInternalSocialLinks()
        enhanceMobileLanguageControl()
      })
      observer.observe(document.body, {childList: true, subtree: true})
    })
    onBeforeUnmount(() => {
      document.removeEventListener('click', handleMobileLanguageClick, true)
      document.removeEventListener('click', closeScreenAfterMobileAppearance)
    })
    watch(() => route.path, () => {
      initZoom()
      wrapButtons()
      scaleDividers()
      scaleCover()
      fixInternalSocialLinks()
      enhanceMobileLanguageControl()
    })
    // 窗口尺寸变化（响应式）时重新缩放扉页/封面
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', scaleDividers)
      window.addEventListener('resize', scaleCover)
    }
  },
}

export default theme
