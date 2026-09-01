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
    const figuresLayout = route.path === '/figures' || route.path === '/figures/'
      || route.path === '/en/figures' || route.path === '/en/figures/'
    const immersiveLayout = homeLayout || figuresLayout
    return h(DefaultTheme.Layout, {class: {'dc3-book-immersive-layout': immersiveLayout}}, {
      // 与 online 首页同源的单画布力场：网格挤压、粒子网络和悬浮点阵 Logo
      'home-hero-before': () => h(HeroWaves),
      // 图库首屏复用同一套动态力场；首屏离开视口后组件会自动停画。
      'doc-before': () => figuresLayout
        ? h(HeroWaves, {hostSelector: '.VPContent', variant: 'gallery'})
        : null,
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
    // 剥离内部链接的 target/rel，让 /figures 走站内 SPA 路由（外链不受影响）；
    // 公众号图标指向 /wechat-qrcode.jpg 静态资源：点击被下方弹窗逻辑拦截，
    // 这里保留其 target 作为无 JS 时的退化路径（新标签打开原图）
    const fixInternalSocialLinks = () =>
      nextTick(() => {
        document.querySelectorAll<HTMLAnchorElement>('.VPSocialLink[href^="/"]:not([href$=".jpg"])').forEach((a) => {
          a.removeAttribute('target')
          a.removeAttribute('rel')
        })
      })
    // 公众号图标点击：在当前页弹出二维码弹窗（不再新标签打开原图；悬浮小卡片保留作快速预览）。
    // 文档级委托：桌面导航条 / 平板 extra 菜单 / 移动抽屉里的同一图标都命中；文案随站点语言
    const openWechatModal = (trigger: HTMLAnchorElement) => {
      const en = document.documentElement.lang.startsWith('en')
      const label = trigger.getAttribute('aria-label') || (en ? 'WeChat Official Account' : '微信公众号')
      const closeLabel = en ? 'Close' : '关闭'
      const hint = en ? 'Scan on WeChat to follow' : '微信扫码关注'
      const modal = document.createElement('div')
      modal.className = 'dc3-wechat-modal'
      modal.setAttribute('role', 'dialog')
      modal.setAttribute('aria-modal', 'true')
      modal.setAttribute('aria-label', label)
      modal.innerHTML = `
        <div class="dc3-wechat-modal__scrim"></div>
        <div class="dc3-wechat-modal__card">
          <button class="dc3-wechat-modal__close" type="button" aria-label="${closeLabel}">
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </button>
          <p class="dc3-wechat-modal__title">${label}</p>
          <div class="dc3-wechat-modal__qr"><img src="/wechat-qrcode.jpg" alt="${label}"></div>
          <p class="dc3-wechat-modal__hint">${hint}</p>
        </div>`
      let closed = false
      const close = () => {
        if (closed) return
        closed = true
        document.removeEventListener('keydown', onKey, true)
        document.body.classList.remove('dc3-modal-open')
        modal.classList.add('is-closing')
        window.setTimeout(() => modal.remove(), 170)
        trigger.focus()
      }
      const onKey = (event: KeyboardEvent) => {
        if (event.key === 'Escape') close()
        if (event.key === 'Tab') {
          // 弹窗内唯一可聚焦元素是关闭按钮：把焦点留在弹窗内
          event.preventDefault()
          modal.querySelector<HTMLButtonElement>('.dc3-wechat-modal__close')?.focus()
        }
      }
      modal.querySelector('.dc3-wechat-modal__close')?.addEventListener('click', close)
      modal.querySelector('.dc3-wechat-modal__scrim')?.addEventListener('click', close)
      document.addEventListener('keydown', onKey, true)
      document.body.appendChild(modal)
      document.body.classList.add('dc3-modal-open')
      modal.querySelector<HTMLButtonElement>('.dc3-wechat-modal__close')?.focus()
    }
    const handleWechatIconClick = (event: MouseEvent) => {
      if (event.defaultPrevented || !(event.target instanceof Element)) return
      const link = event.target.closest<HTMLAnchorElement>('.VPSocialLink[href*="wechat-qrcode"]')
      if (!link) return
      event.preventDefault()
      openWechatModal(link)
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
      syncCurrentYear()
      fixInternalSocialLinks()
      currentYearTimer = window.setInterval(syncCurrentYear, 60 * 60 * 1000)
      document.addEventListener('click', closeScreenAfterMobileAppearance)
      document.addEventListener('click', handleWechatIconClick)
      // 抽屉/extra 菜单按需渲染，挂载后再出现的社交链接也要剥离 target
      const observer = new MutationObserver(() => {
        fixInternalSocialLinks()
      })
      observer.observe(document.body, {childList: true, subtree: true})
    })
    onBeforeUnmount(() => {
      document.removeEventListener('click', closeScreenAfterMobileAppearance)
      document.removeEventListener('click', handleWechatIconClick)
      // 卸载时若弹窗仍开着，直接移除并恢复页面滚动
      document.querySelector('.dc3-wechat-modal')?.remove()
      document.body.classList.remove('dc3-modal-open')
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
