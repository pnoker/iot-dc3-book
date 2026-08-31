import {onBeforeUnmount, onMounted} from 'vue'

const headerProperties = [
  '--dc3-nav-progress',
  '--dc3-nav-width',
  '--dc3-nav-height',
  '--dc3-nav-offset',
  '--dc3-nav-padding',
]

export function useImmersiveHeader() {
  let frame = 0
  let progress = 0
  let targetProgress = 0
  let reducedMotion = false
  let headerContainer: HTMLElement | null = null
  let startWidth = 0
  let endWidth = 0
  let endPadding = 12

  function easedProgress(scrollY: number) {
    const raw = Math.min(1, Math.max(0, (scrollY - 4) / 96))
    return raw * raw * (3 - 2 * raw)
  }

  function resolveHeaderContainer() {
    headerContainer = document.querySelector<HTMLElement>('.VPNavBar > .wrapper > .container')
    return headerContainer
  }

  function measureGeometry() {
    const viewportWidth = document.querySelector<HTMLElement>('.dc3-book-immersive-layout')?.getBoundingClientRect().width
      || document.documentElement.clientWidth
    const compact = viewportWidth < 768
    const medium = viewportWidth >= 768 && viewportWidth < 1280
    const startGutter = compact ? 24 : medium ? 48 : 64
    const responsiveStartWidth = compact || medium
      ? viewportWidth - startGutter
      : Math.min(1360, viewportWidth - startGutter)
    const contentWidth = document.querySelector<HTMLElement>('.book-home-container')?.getBoundingClientRect().width
      || document.querySelector<HTMLElement>('.figure-gallery')?.getBoundingClientRect().width
      || document.querySelector<HTMLElement>('.VPHero .container')?.getBoundingClientRect().width

    startWidth = responsiveStartWidth
    endWidth = contentWidth || Math.min(1152, viewportWidth - startGutter)
    endPadding = compact ? 8 : medium ? 10 : 12
  }

  function applyProgress(nextProgress: number) {
    const target = headerContainer || resolveHeaderContainer()
    if (!target) return
    target.style.setProperty('--dc3-nav-progress', nextProgress.toFixed(4))

    if (nextProgress < 0.0001) {
      headerProperties.slice(1).forEach((property) => target.style.removeProperty(property))
      return
    }

    target.style.setProperty('--dc3-nav-width', `${startWidth + (endWidth - startWidth) * nextProgress}px`)
    target.style.setProperty('--dc3-nav-height', `${64 - 12 * nextProgress}px`)
    target.style.setProperty('--dc3-nav-offset', `${6 * nextProgress}px`)
    target.style.setProperty('--dc3-nav-padding', `${endPadding * nextProgress}px`)
  }

  function animate() {
    const delta = targetProgress - progress
    progress += delta * 0.18
    if (Math.abs(delta) < 0.001) progress = targetProgress
    applyProgress(progress)

    if (progress !== targetProgress) frame = requestAnimationFrame(animate)
    else {
      frame = 0
      headerContainer?.classList.remove('dc3-nav-animating')
    }
  }

  function syncState() {
    targetProgress = easedProgress(window.scrollY)
    if (progress < 0.0001 && targetProgress > 0) measureGeometry()

    if (reducedMotion) {
      progress = targetProgress
      applyProgress(progress)
      return
    }
    if (!frame) {
      headerContainer?.classList.add('dc3-nav-animating')
      frame = requestAnimationFrame(animate)
    }
  }

  function syncViewport() {
    resolveHeaderContainer()
    measureGeometry()
    applyProgress(progress)
  }

  onMounted(() => {
    // 变量只挂在 Header 容器上，避免 Figures 页的上万个 SVG 节点参与每帧样式重算。
    headerProperties.forEach((property) => document.documentElement.style.removeProperty(property))
    document.documentElement.classList.remove('dc3-nav-animating')
    resolveHeaderContainer()
    measureGeometry()
    reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    progress = easedProgress(window.scrollY)
    targetProgress = progress
    applyProgress(progress)
    window.addEventListener('scroll', syncState, {passive: true})
    window.addEventListener('resize', syncViewport, {passive: true})
  })

  onBeforeUnmount(() => {
    cancelAnimationFrame(frame)
    window.removeEventListener('scroll', syncState)
    window.removeEventListener('resize', syncViewport)
    document.documentElement.classList.remove('dc3-nav-animating')
    headerContainer?.classList.remove('dc3-nav-animating')
    headerProperties.forEach((property) => headerContainer?.style.removeProperty(property))
    headerContainer = null
  })
}
