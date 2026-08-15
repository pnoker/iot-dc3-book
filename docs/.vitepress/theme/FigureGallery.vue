<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

interface FigureItem {
  id: string
  num: string
  title: string
  chapter: number
  chapterTitle: string
  url: string
  thumb: string
}

const items = ref<FigureItem[]>([])
const query = ref('')
const activeIndex = ref(-1)
const loading = ref(true)
const error = ref('')

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter((it) =>
    [it.num, it.title, it.chapterTitle, String(it.chapter)].some((s) =>
      s.toLowerCase().includes(q),
    ),
  )
})

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
    const res = await fetch('/figures-manifest.json')
    if (!res.ok) throw new Error(String(res.status))
    items.value = await res.json()
  } catch {
    error.value = '图库清单加载失败，请稍后重试'
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
          placeholder="搜索图号、标题或章节…"
          aria-label="搜索插图"
        />
      </label>
      <div class="gallery-count">
        <template v-if="loading">加载中…</template>
        <template v-else>共 {{ filtered.length }} 张插图</template>
      </div>
    </div>

    <p v-if="loading" class="gallery-hint">正在加载全书插图清单…</p>
    <p v-else-if="error" class="gallery-hint">{{ error }}</p>
    <p v-else-if="!filtered.length" class="gallery-hint">没有匹配「{{ query }}」的插图</p>

    <template v-else>
      <section v-for="[ch, list] in grouped" :key="ch" class="gallery-group">
        <h2 class="gallery-group-title">
          <span class="gallery-group-no">第 {{ ch }} 章</span>
          <span class="gallery-group-name">{{ list[0].chapterTitle }}</span>
          <span class="gallery-group-count">{{ list.length }} 张</span>
        </h2>
        <div class="gallery-grid">
          <article
            v-for="item in list"
            :key="item.id"
            class="fig-card"
            @click="openLightbox(item)"
          >
            <div class="fig-thumb">
              <img :src="item.thumb" :alt="`${item.num} ${item.title}`" loading="lazy" />
            </div>
            <div class="fig-meta">
              <div class="fig-num">{{ item.num }}</div>
              <div class="fig-title">{{ item.title }}</div>
            </div>
            <a class="fig-jump" :href="item.url" @click.stop :title="'前往原文 · ' + item.num">
              前往原文 →
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
      :aria-label="active.num + ' ' + active.title"
    >
      <button class="lb-btn lb-close" @click="closeLightbox" aria-label="关闭">×</button>
      <button class="lb-btn lb-nav lb-prev" @click="prev" aria-label="上一张">‹</button>
      <figure class="lb-figure">
        <img :src="active.thumb" :alt="`${active.num} ${active.title}`" />
        <figcaption>
          <span class="lb-num">{{ active.num }}</span>
          <span class="lb-title">{{ active.title }}</span>
          <span class="lb-chapter">第 {{ active.chapter }} 章 · {{ active.chapterTitle }}</span>
          <a class="lb-jump" :href="active.url">前往原文 →</a>
        </figcaption>
      </figure>
      <button class="lb-btn lb-nav lb-next" @click="next" aria-label="下一张">›</button>
    </div>
  </section>
</template>

<style scoped>
.figure-gallery {
  max-width: 1200px;
  margin: 0 auto;
}

/* 工具栏：搜索 + 计数 */
.gallery-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
  flex-wrap: wrap;
}
.gallery-search {
  position: relative;
  flex: 1 1 360px;
  max-width: 560px;
  display: flex;
  align-items: center;
}
.gallery-search-icon {
  position: absolute;
  left: 14px;
  width: 18px;
  height: 18px;
  fill: none;
  stroke: var(--vp-c-text-2);
  stroke-width: 2;
  pointer-events: none;
}
.gallery-search input {
  width: 100%;
  padding: 10px 16px 10px 42px;
  font-size: 14px;
  color: var(--vp-c-text-1);
  background: var(--vp-c-bg-alt);
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.gallery-search input:focus {
  border-color: var(--vp-c-brand);
  box-shadow: 0 0 0 3px var(--vp-c-brand-soft, rgba(37, 99, 235, 0.12));
}
.gallery-search input::placeholder {
  color: var(--vp-c-text-3);
}
.gallery-count {
  font-size: 13px;
  color: var(--vp-c-text-2);
  white-space: nowrap;
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
}
.fig-thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
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
  .lb-figure img {
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
