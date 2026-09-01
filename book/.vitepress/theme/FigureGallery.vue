<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

interface FigureItem {
  id: string
  num: string
  numEn?: string
  title: string
  titleEn?: string
  chapter: number
  chapterTitle: string
  chapterTitleEn?: string
  url: string
  thumb: string
}

const props = withDefaults(defineProps<{lang?: 'zh' | 'en'}>(), {lang: 'zh'})
const en = computed(() => props.lang === 'en')
const t = (zh: string, enText: string) => (en.value ? enText : zh)

const items = ref<FigureItem[]>([])
const svgs = ref<Record<string, string>>({})
const query = ref('')
const activeIndex = ref(-1)
const loading = ref(true)
const error = ref('')

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter((it) =>
    [
      it.num, it.numEn, it.title, it.titleEn,
      it.chapterTitle, it.chapterTitleEn, String(it.chapter),
    ].some((s) => (s || '').toLowerCase().includes(q)),
  )
})

const numOf = (it: FigureItem) => (en.value ? it.numEn || it.num : it.num)
const titleOf = (it: FigureItem) => (en.value ? it.titleEn || it.title : it.title)
const chTitleOf = (it: FigureItem) =>
  en.value ? it.chapterTitleEn || it.chapterTitle : it.chapterTitle
const urlOf = (it: FigureItem) =>
  en.value && !it.url.startsWith('/en/') ? '/en' + it.url : it.url

const grouped = computed(() => {
  const map = new Map<number, FigureItem[]>()
  for (const it of filtered.value) {
    if (!map.has(it.chapter)) map.set(it.chapter, [])
    map.get(it.chapter)!.push(it)
  }
  return [...map.entries()].sort((a, b) => a[0] - b[0])
})

const active = computed(() =>
  activeIndex.value >= 0 && activeIndex.value < filtered.value.length
    ? filtered.value[activeIndex.value]
    : null,
)

const openLightbox = (item: FigureItem) => {
  activeIndex.value = filtered.value.indexOf(item)
}
const closeLightbox = () => {
  activeIndex.value = -1
}
const next = () => {
  const n = filtered.value.length
  activeIndex.value = n ? (activeIndex.value + 1) % n : -1
}
const prev = () => {
  const n = filtered.value.length
  activeIndex.value = n ? (activeIndex.value - 1 + n) % n : -1
}

const onKey = (e: KeyboardEvent) => {
  if (activeIndex.value < 0) return
  if (e.key === 'Escape') closeLightbox()
  else if (e.key === 'ArrowRight') next()
  else if (e.key === 'ArrowLeft') prev()
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try {
    const [manifestRes, svgRes] = await Promise.all([
      fetch('/figures-manifest.json'),
      fetch(en.value ? '/figures-svg-en.json' : '/figures-svg.json'),
    ])
    if (!manifestRes.ok) throw new Error(String(manifestRes.status))
    items.value = await manifestRes.json()
    // SVG 清单加载失败不阻塞图库
    if (svgRes.ok) svgs.value = await svgRes.json()
  } catch {
    error.value = t('图库清单加载失败，请稍后重试', 'Failed to load the figure list — please retry')
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <section class="figure-gallery">
    <div class="gallery-toolbar">
      <label class="gallery-search">
        <svg class="gallery-search-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <line x1="16.5" y1="16.5" x2="21" y2="21" />
        </svg>
        <input
          v-model="query"
          type="search"
          :placeholder="t('搜索图号、标题或章节…', 'Search by number, title, or chapter…')"
          :aria-label="t('搜索插图', 'Search figures')"
        />
        <span class="gallery-count" aria-live="polite">
          <template v-if="loading">{{ t('加载中…', 'Loading…') }}</template>
          <template v-else>{{ t(`共 ${filtered.length} 张插图`, `${filtered.length} figures`) }}</template>
        </span>
      </label>
    </div>

    <p v-if="loading" class="gallery-hint">{{ t('正在加载全书插图清单…', 'Loading the figure list…') }}</p>
    <p v-else-if="error" class="gallery-hint">{{ error }}</p>
    <p v-else-if="!filtered.length" class="gallery-hint">{{ t(`没有匹配「${query}」的插图`, `No figures match “${query}”`) }}</p>

    <template v-else>
      <section v-for="[ch, list] in grouped" :key="ch" class="gallery-group">
        <h2 class="gallery-group-title">
          <span class="gallery-group-no">{{ t(`第 ${ch} 章`, `Chapter ${ch}`) }}</span>
          <span class="gallery-group-name">{{ chTitleOf(list[0]) }}</span>
          <span class="gallery-group-count">{{ t(`${list.length} 张`, `${list.length} figures`) }}</span>
        </h2>
        <div class="gallery-grid">
          <article
            v-for="item in list"
            :key="item.id"
            class="fig-card"
            @click="openLightbox(item)"
          >
            <div class="fig-thumb">
              <div
                v-if="svgs[item.id]"
                class="fig-svg"
                :aria-label="numOf(item) + ' ' + titleOf(item)"
                role="img"
                v-html="svgs[item.id]"
              ></div>
            </div>
            <div class="fig-meta">
              <div class="fig-num">{{ numOf(item) }}</div>
              <div class="fig-title">{{ titleOf(item) }}</div>
            </div>
            <a class="fig-jump" :href="urlOf(item)" @click.stop :title="t('前往原文 · ', 'Open in text · ') + numOf(item)">
              {{ t('前往原文 →', 'Open in text →') }}
            </a>
          </article>
        </div>
      </section>
    </template>

    <div
      v-if="active"
      class="fig-lightbox"
      @click.self="closeLightbox"
      role="dialog"
      aria-modal="true"
      :aria-label="numOf(active) + ' ' + titleOf(active)"
    >
      <button class="lb-btn lb-close" @click="closeLightbox" :aria-label="t('关闭', 'Close')">×</button>
      <button class="lb-btn lb-nav lb-prev" @click="prev" :aria-label="t('上一张', 'Previous')">‹</button>
      <figure class="lb-figure">
        <div v-if="svgs[active.id]" class="lb-svg" v-html="svgs[active.id]"></div>
        <figcaption>
          <span class="lb-num">{{ numOf(active) }}</span>
          <span class="lb-title">{{ titleOf(active) }}</span>
          <span class="lb-chapter">{{ t(`第 ${active.chapter} 章`, `Chapter ${active.chapter}`) }} · {{ chTitleOf(active) }}</span>
          <a class="lb-jump" :href="urlOf(active)">{{ t('前往原文 →', 'Open in text →') }}</a>
        </figcaption>
      </figure>
      <button class="lb-btn lb-nav lb-next" @click="next" :aria-label="t('下一张', 'Next')">›</button>
    </div>
  </section>
</template>

<style scoped>
.figure-gallery {
  max-width: 1200px;
  margin: 0 auto;
}

/* 工具栏：不带任何整条底色——氛围背景直接透出，吸附时只有胶囊自身玻璃化，
   避免亮色下白带 / 暗色下黑带的"大方块"感 */
.gallery-toolbar {
  position: sticky;
  top: var(--vp-nav-height);
  z-index: 20;
  display: flex;
  margin-bottom: 24px;
}
/* 玻璃胶囊：图标 + 输入 + 计数同舱，与沉浸式导航胶囊同语言 */
.gallery-search {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 42px;
  padding: 0 16px 0 17px;
  background: color-mix(in srgb, var(--vp-c-bg-elv) 58%, transparent);
  border: 1px solid color-mix(in srgb, var(--vp-c-divider) 78%, transparent);
  border-radius: 999px;
  box-shadow: inset 0 1px 0 color-mix(in srgb, #ffffff 42%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
  cursor: text;
}
.gallery-search:hover {
  border-color: color-mix(in srgb, var(--vp-c-brand-3) 38%, var(--vp-c-divider));
}
.gallery-search:focus-within {
  background: color-mix(in srgb, var(--vp-c-bg-elv) 86%, transparent);
  border-color: var(--vp-c-brand-1);
  box-shadow:
    0 0 0 3px var(--vp-c-brand-soft),
    inset 0 1px 0 color-mix(in srgb, #ffffff 42%, transparent);
}
.gallery-search-icon {
  flex: none;
  width: 17px;
  height: 17px;
  fill: none;
  stroke: var(--vp-c-brand-1);
  stroke-width: 2;
  stroke-linecap: round;
  pointer-events: none;
}
.gallery-search input {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 0;
  font-size: 14px;
  color: var(--vp-c-text-1);
  background: transparent;
  border: none;
  outline: none;
  box-shadow: none;
}
.gallery-search input::placeholder {
  color: var(--vp-c-text-3);
}
.gallery-count {
  flex: none;
  margin-left: 4px;
  padding-left: 14px;
  border-left: 1px solid color-mix(in srgb, var(--vp-c-divider) 70%, transparent);
  font-size: 12.5px;
  color: var(--vp-c-text-3);
  white-space: nowrap;
}
@media (max-width: 560px) {
  .gallery-count {
    display: none;
  }
}

.gallery-hint {
  padding: 48px 0;
  text-align: center;
  color: var(--vp-c-text-2);
  font-size: 14px;
}

/* 章节分组 */
.gallery-group {
  margin-bottom: 40px;
}
.gallery-group-title {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin: 0 0 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--vp-c-divider);
  font-size: 17px;
  font-weight: 600;
  color: var(--vp-c-text-1);
}
.gallery-group-no {
  color: var(--vp-c-brand);
}
.gallery-group-name {
  font-weight: 500;
  color: var(--vp-c-text-2);
}
.gallery-group-count {
  margin-left: auto;
  font-size: 12px;
  font-weight: 400;
  color: var(--vp-c-text-3);
}

/* 网格 + 卡片 */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 18px;
}
.fig-card {
  position: relative;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-alt);
  overflow: hidden;
  cursor: zoom-in;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.fig-card:hover {
  transform: translateY(-2px);
  border-color: var(--vp-c-brand);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}
.fig-thumb {
  aspect-ratio: 3 / 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--vp-c-bg);
  border-bottom: 1px solid var(--vp-c-divider);
  overflow: hidden;
}
.fig-thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
/* 内联 SVG 缩略图：矢量 + 跟随明暗主题（fill/stroke 走 figures.css 变量） */
.fig-svg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.fig-svg :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}
.fig-meta {
  padding: 12px 14px 40px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.fig-num {
  font-size: 12px;
  font-weight: 600;
  color: var(--vp-c-brand);
}
.fig-title {
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--vp-c-text-1);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.fig-jump {
  position: absolute;
  left: 14px;
  bottom: 12px;
  font-size: 12px;
  color: var(--vp-c-brand);
  text-decoration: none;
  opacity: 0.85;
}
.fig-jump:hover {
  opacity: 1;
  text-decoration: underline;
}

/* 灯箱 */
.fig-lightbox {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: rgba(0, 0, 0, 0.78);
}
.lb-btn {
  position: absolute;
  border: none;
  cursor: pointer;
  color: #fff;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease;
}
.lb-btn:hover {
  background: rgba(255, 255, 255, 0.24);
}
.lb-close {
  top: 20px;
  right: 24px;
  width: 44px;
  height: 44px;
  font-size: 28px;
  line-height: 1;
}
.lb-nav {
  top: 50%;
  transform: translateY(-50%);
  width: 52px;
  height: 52px;
  font-size: 34px;
  line-height: 1;
}
.lb-prev {
  left: 20px;
}
.lb-next {
  right: 20px;
}
.lb-figure {
  margin: 0;
  max-width: min(1400px, 90vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.lb-figure img {
  max-width: 100%;
  max-height: 76vh;
  object-fit: contain;
  border-radius: 6px;
  background: #fff;
}
/* 灯箱内联 SVG：跟随明暗主题，清晰放大 */
.lb-svg {
  max-width: 100%;
  max-height: 76vh;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  overflow: hidden;
}
.lb-svg :deep(svg) {
  max-width: 100%;
  max-height: 76vh;
  width: auto;
  height: auto;
}
.lb-figure figcaption {
  margin-top: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  color: #e2e8f0;
  font-size: 13px;
  text-align: center;
}
.lb-num {
  font-weight: 700;
  color: #fff;
}
.lb-chapter {
  color: #94a3b8;
}
.lb-jump {
  padding: 4px 12px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 999px;
  color: #fff;
  text-decoration: none;
  font-size: 12px;
}
.lb-jump:hover {
  background: rgba(255, 255, 255, 0.14);
}

@media (max-width: 768px) {
  .fig-lightbox {
    padding: 16px;
  }
  .lb-figure img,
  .lb-svg :deep(svg) {
    max-height: 68vh;
  }
  .lb-nav {
    width: 40px;
    height: 40px;
    font-size: 26px;
  }
  .lb-prev {
    left: 8px;
  }
  .lb-next {
    right: 8px;
  }
}
</style>
