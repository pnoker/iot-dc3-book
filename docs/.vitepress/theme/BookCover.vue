<script setup lang="ts">
import {computed} from 'vue'

const props = defineProps<{english: boolean}>()

const highlightColors = ['#2563eb', '#10b981', '#f59e0b', '#2563eb']
const copy = computed(() => props.english ? {
  lang: 'en',
  tag: 'CONNECTED INTELLIGENCE',
  tagWidth: 164,
  title: [
    {text: 'AIoT', y: 106},
    {text: 'Technology', y: 140},
    {text: '& Practice', y: 174}
  ],
  titleSize: 34,
  titleSpacing: 0,
  subtitle: 'From IoT Platforms to Agent Applications',
  subtitleSize: 10.5,
  subtitleY: 211,
  highlights: [
    'Five layers · Intelligence · IoT platform foundation',
    'LLMs · Agent · MCP · Tools · Skills · CLI · Intelligent Ops',
    'IoT DC3 open source throughout the book',
    '14 chapters · 72 architecture diagrams · Engineering methods'
  ],
  highlightSize: 7.2,
  author: 'Henry Zhang',
  authorTitle: 'IoT DC3 Creator · Architect · IoT Expert',
  pageKicker: 'AIoT STACK',
  pageTitle: 'Five-layer architecture',
  pageSubtitle: 'From devices to intelligence',
  pageLayers: ['Applications', 'Intelligence', 'Platform', 'Connectivity', 'Devices'],
  pageLoop: 'Sense · Decide · Act · Feedback',
  brand: ['From Connectivity to', 'Intelligence'],
  brandSub: 'IoT DC3'
} : {
  lang: 'zh-CN',
  tag: '万物智联',
  tagWidth: 62,
  title: [
    {text: 'AIoT', y: 112},
    {text: '技术与实践', y: 157}
  ],
  titleSize: 41,
  titleSpacing: 1.5,
  subtitle: '—— 从物联网平台到智能体应用',
  subtitleSize: 12.5,
  subtitleY: 204,
  highlights: [
    '五层架构 · 智能层 · 物联网平台底座',
    '大模型 · Agent · MCP · Tools · Skills · CLI · 智能运维',
    'IoT DC3 开源项目贯穿全书',
    '14 章 · 72 张架构图 · 工程方法论'
  ],
  highlightSize: 7.6,
  author: '张红元',
  authorTitle: 'IoT DC3 开源作者 · 架构师 · 物联网专家',
  pageKicker: 'AIoT STACK',
  pageTitle: '五层架构',
  pageSubtitle: '从设备接入到智能决策',
  pageLayers: ['应用层', '智能层', '平台层', '连接层', '设备层'],
  pageLoop: '感知 · 决策 · 执行 · 反馈',
  brand: ['从连接到智能'],
  brandSub: 'Connecting to Intelligence'
})
</script>

<template>
  <span class="book-visual" aria-hidden="true">
    <span class="book-page">
      <span class="page-meta">
        <span>{{ copy.pageKicker }}</span>
        <span>01</span>
      </span>
      <strong class="page-title">{{ copy.pageTitle }}</strong>
      <span class="page-subtitle">{{ copy.pageSubtitle }}</span>
      <span class="page-layers">
        <span v-for="layer in copy.pageLayers" :key="layer" class="page-layer">
          <span class="page-layer-dot"></span>
          <span>{{ layer }}</span>
        </span>
      </span>
      <span class="page-loop">{{ copy.pageLoop }}</span>
    </span>

    <span class="book-front">
      <svg
        class="book-cover-art"
        :lang="copy.lang"
        viewBox="0 0 480 680"
        preserveAspectRatio="xMidYMid meet"
      >
    <defs>
      <linearGradient id="book-cover-background" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#eef4ff" />
        <stop offset="0.34" stop-color="#e0f2fe" />
        <stop offset="0.63" stop-color="#f0fbff" />
        <stop offset="1" stop-color="#fef6ec" />
      </linearGradient>
      <linearGradient id="book-cover-title" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#1d4ed8" />
        <stop offset="0.58" stop-color="#0891b2" />
        <stop offset="1" stop-color="#059669" />
      </linearGradient>
      <linearGradient id="book-cover-divider" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#2563eb" />
        <stop offset="0.56" stop-color="#10b981" />
        <stop offset="1" stop-color="#f59e0b" />
      </linearGradient>
      <radialGradient id="book-cover-blue-glow">
        <stop offset="0" stop-color="#60a5fa" stop-opacity="0.34" />
        <stop offset="1" stop-color="#60a5fa" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="book-cover-green-glow">
        <stop offset="0" stop-color="#34d399" stop-opacity="0.25" />
        <stop offset="1" stop-color="#34d399" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="book-cover-amber-glow">
        <stop offset="0" stop-color="#fbbf24" stop-opacity="0.2" />
        <stop offset="1" stop-color="#fbbf24" stop-opacity="0" />
      </radialGradient>
      <pattern id="book-cover-grid" width="20" height="20" patternUnits="userSpaceOnUse">
        <path d="M20 0H0V20" fill="none" stroke="#2563eb" stroke-opacity="0.055" stroke-width="0.7" />
      </pattern>
    </defs>

    <rect width="480" height="680" fill="url(#book-cover-background)" />
    <rect width="480" height="680" fill="url(#book-cover-grid)" />
    <circle cx="448" cy="52" r="145" fill="url(#book-cover-blue-glow)" />
    <circle cx="22" cy="656" r="138" fill="url(#book-cover-green-glow)" />
    <circle cx="474" cy="405" r="116" fill="url(#book-cover-amber-glow)" />

    <g class="constellation primary">
      <path d="M326 92L365 72L403 96L442 82M403 96L428 132L389 150L350 136L326 92M389 150L416 192L365 206L333 177L350 136" />
      <path class="orbit" d="M326 92C360 52 431 55 449 100C461 134 435 187 395 207" />
      <circle cx="326" cy="92" r="4" class="blue" />
      <circle cx="365" cy="72" r="3" class="cyan" />
      <circle cx="403" cy="96" r="4.5" class="teal" />
      <circle cx="442" cy="82" r="3" class="green" />
      <circle cx="428" cy="132" r="4.5" class="cyan" />
      <circle cx="389" cy="150" r="5" class="blue" />
      <circle cx="416" cy="192" r="4" class="green" />
      <circle cx="365" cy="206" r="3.5" class="amber" />
      <circle cx="333" cy="177" r="3" class="blue" />
      <circle cx="350" cy="136" r="3.5" class="teal" />
    </g>

    <g class="constellation secondary">
      <path d="M455 355L422 405L452 443L390 470L330 450L282 500M422 405L390 470L350 510" />
      <path class="orbit" d="M455 355C430 365 411 389 405 425C398 467 365 500 326 516" />
      <circle cx="455" cy="355" r="3.5" class="green" />
      <circle cx="422" cy="405" r="3" class="cyan" />
      <circle cx="452" cy="443" r="3.5" class="amber" />
      <circle cx="390" cy="470" r="4" class="teal" />
      <circle cx="330" cy="450" r="3.5" class="blue" />
      <circle cx="350" cy="510" r="2.8" class="green" />
      <circle cx="282" cy="500" r="3.5" class="blue" />
    </g>

    <g class="cover-copy">
      <rect x="50" y="58" :width="copy.tagWidth" height="20" rx="10" class="tag-outline" />
      <text :x="50 + copy.tagWidth / 2" y="68" class="tag-text">{{ copy.tag }}</text>

      <text
        v-for="line in copy.title"
        :key="line.text"
        x="50"
        :y="line.y"
        class="cover-title"
        :font-size="copy.titleSize"
        :letter-spacing="copy.titleSpacing"
      >{{ line.text }}</text>

      <text x="50" :y="copy.subtitleY" class="cover-subtitle" :font-size="copy.subtitleSize">{{ copy.subtitle }}</text>
      <rect x="50" y="242" width="49" height="3" rx="1.5" fill="url(#book-cover-divider)" />

      <g v-for="(highlight, index) in copy.highlights" :key="highlight">
        <circle cx="52.5" :cy="278 + index * 21" r="2.6" :fill="highlightColors[index]" />
        <text x="63" :y="278 + index * 21" class="cover-highlight" :font-size="copy.highlightSize">{{ highlight }}</text>
      </g>
    </g>

    <g class="cover-footer">
      <g class="logo-mark" transform="translate(50 586)">
        <circle cx="14" cy="14" r="4.2" fill="#0891b2" />
        <circle cx="4" cy="14" r="2.2" fill="#2563eb" />
        <circle cx="24" cy="14" r="2.2" fill="#10b981" />
        <circle cx="9" cy="5" r="2.2" fill="#06b6d4" />
        <circle cx="19" cy="5" r="2.2" fill="#2563eb" />
        <circle cx="9" cy="23" r="2.2" fill="#10b981" />
        <circle cx="19" cy="23" r="2.2" fill="#06b6d4" />
        <path d="M4 14L9 5L19 5L24 14L19 23L9 23Z" fill="none" stroke="#0891b2" stroke-width="1.3" opacity="0.72" />
      </g>
      <text x="90" y="598" class="author-name">{{ copy.author }}</text>
      <text x="90" y="614" class="author-title">{{ copy.authorTitle }}</text>

      <text
        v-for="(line, index) in copy.brand"
        :key="line"
        x="430"
        :y="598 + index * 11"
        class="brand-title"
      >{{ line }}</text>
      <text x="430" :y="copy.brand.length > 1 ? 626 : 614" class="brand-subtitle">{{ copy.brandSub }}</text>
    </g>
      </svg>
    </span>
  </span>
</template>

<style scoped>
.book-visual {
  position: absolute;
  inset: 0;
  display: block;
  border-radius: inherit;
  transform-style: preserve-3d;
}

.book-page,
.book-front {
  position: absolute;
  inset: 0;
  border-radius: inherit;
}

.book-page {
  overflow: hidden;
  padding: 10px 9px 8px;
  border: 1px solid rgba(111, 173, 218, 0.24);
  background:
    radial-gradient(circle at 82% 10%, rgba(56, 189, 248, 0.16), transparent 32%),
    linear-gradient(145deg, #f8fcff, #edf7fb 62%, #f8fbf4);
  box-shadow:
    -4px 4px 0 rgba(55, 102, 172, 0.11),
    0 19px 34px rgba(25, 91, 153, 0.19),
    0 5px 11px rgba(25, 91, 153, 0.1),
    inset 10px 0 18px rgba(58, 115, 169, 0.06);
  color: #334155;
}

.book-page::before {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(37, 99, 235, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(37, 99, 235, 0.045) 1px, transparent 1px);
  background-size: 12px 12px;
  content: '';
}

.book-page > * {
  position: relative;
  z-index: 1;
}

.page-meta {
  display: flex;
  justify-content: space-between;
  color: #0284c7;
  font-size: 5px;
  font-weight: 760;
  letter-spacing: 0.12em;
}

.page-title,
.page-subtitle,
.page-loop {
  display: block;
}

.page-title {
  margin-top: 7px;
  color: #0f3f78;
  font-size: 10px;
  line-height: 1.15;
}

.page-subtitle {
  margin-top: 3px;
  color: #64748b;
  font-size: 5.5px;
  line-height: 1.3;
}

.page-layers {
  display: grid;
  gap: 3px;
  margin-top: 9px;
}

.page-layer {
  display: flex;
  gap: 6px;
  align-items: center;
  min-height: 15px;
  padding: 3px 6px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 5px;
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.11), rgba(255, 255, 255, 0.62));
  color: #3730a3;
  font-size: 6px;
  font-weight: 680;
  line-height: 1;
}

.page-layer:nth-child(2) {
  border-color: rgba(20, 184, 166, 0.14);
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.12), rgba(255, 255, 255, 0.62));
  color: #0f766e;
}

.page-layer:nth-child(3) {
  border-color: rgba(37, 99, 235, 0.14);
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.11), rgba(255, 255, 255, 0.62));
  color: #1d4ed8;
}

.page-layer:nth-child(4) {
  border-color: rgba(8, 145, 178, 0.14);
  background: linear-gradient(90deg, rgba(8, 145, 178, 0.1), rgba(255, 255, 255, 0.62));
  color: #0e7490;
}

.page-layer:nth-child(5) {
  border-color: rgba(71, 85, 105, 0.12);
  background: linear-gradient(90deg, rgba(71, 85, 105, 0.09), rgba(255, 255, 255, 0.62));
  color: #334155;
}

.page-layer-dot {
  width: 5px;
  height: 5px;
  border: 1px solid currentColor;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.72);
}

.page-loop {
  margin-top: 8px;
  color: #0891b2;
  font-size: 5px;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-align: center;
}

.book-front {
  z-index: 2;
  box-shadow:
    -4px 4px 0 rgba(55, 102, 172, 0.13),
    0 19px 34px rgba(25, 91, 153, 0.2),
    0 5px 11px rgba(25, 91, 153, 0.12);
  transform-origin: left center;
  transform-style: preserve-3d;
  animation: book-invite 1.25s 480ms both;
  transition: transform 760ms cubic-bezier(0.2, 0.72, 0.18, 1), box-shadow 760ms ease;
}

.book-front::before,
.book-front::after {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  backface-visibility: hidden;
  content: '';
  pointer-events: none;
}

.book-front::before {
  border: 1px solid rgba(123, 178, 214, 0.22);
  background:
    repeating-linear-gradient(to bottom, transparent 0 13px, rgba(72, 112, 145, 0.11) 13px 14px),
    linear-gradient(145deg, #f8fcff, #edf7fb);
  box-shadow: inset -10px 0 18px rgba(58, 115, 169, 0.06);
  transform: rotateY(180deg) translateZ(1px);
}

.book-front::after {
  border: 1px solid rgba(255, 255, 255, 0.7);
  background: linear-gradient(115deg, rgba(255, 255, 255, 0.24), transparent 34%);
  transform: translateZ(2px);
}

.book-cover-art {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background: #eef4ff;
  backface-visibility: hidden;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  shape-rendering: geometricPrecision;
  text-rendering: geometricPrecision;
  transform: translateZ(1px);
}

.constellation path {
  fill: none;
  stroke: #38bdf8;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-opacity: 0.48;
  stroke-width: 1.1;
}

.constellation .orbit {
  stroke: #2563eb;
  stroke-dasharray: 2 6;
  stroke-opacity: 0.12;
  stroke-width: 0.8;
}

.constellation circle {
  stroke: #fff;
  stroke-width: 1.2;
}

.constellation .blue { fill: #2563eb; }
.constellation .cyan { fill: #06b6d4; }
.constellation .teal { fill: #0891b2; }
.constellation .green { fill: #10b981; }
.constellation .amber { fill: #f59e0b; }

.tag-outline {
  fill: rgba(255, 255, 255, 0.52);
  stroke: rgba(37, 99, 235, 0.42);
  stroke-width: 1;
}

.tag-text {
  fill: #2563eb;
  font-size: 6.5px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-anchor: middle;
  dominant-baseline: middle;
}

.cover-title {
  fill: url(#book-cover-title);
  font-weight: 800;
  dominant-baseline: middle;
}

.cover-subtitle {
  fill: #334155;
  font-weight: 450;
  dominant-baseline: middle;
}

.cover-highlight {
  fill: #475569;
  font-weight: 520;
  dominant-baseline: middle;
}

.author-name {
  fill: #0f172a;
  font-size: 11px;
  font-weight: 750;
  dominant-baseline: middle;
}

.author-title {
  fill: #64748b;
  font-size: 6px;
  font-weight: 450;
  letter-spacing: 0.15px;
  dominant-baseline: middle;
}

.brand-title,
.brand-subtitle {
  text-anchor: end;
  dominant-baseline: middle;
}

.brand-title {
  fill: #0891b2;
  font-size: 8px;
  font-weight: 720;
}

.brand-subtitle {
  fill: #94a3b8;
  font-size: 6.5px;
  letter-spacing: 0.8px;
}

@keyframes book-invite {
  0%, 100% { transform: rotateY(0); }
  52% { transform: rotateY(-16deg); }
}

@media (prefers-reduced-motion: reduce) {
  .book-front {
    animation: none;
    transition: none;
  }

}
</style>
