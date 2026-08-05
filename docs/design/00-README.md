# 《从工业软件到 AI 智能体》书籍网站 · 设计总览

> 部署域名：**book.dc3.site**　·　参考站点：`iot-dc3-online`　·　技术栈：VitePress
> 本文是设计入口；分项细节见同目录其余文档。

---

## 1. 我们要做什么

把 `iot-dc3-book/output/` 下导出的书籍 **《从工业软件到 AI 智能体》**（副标题「AIoT 技术与实践 —— 从物联网平台到智能体应用」，作者张红元）做成一个**在线阅读站**：

- 内容：封面 / 作者简介 / 序 / 导读 / 目录 / 附录 + **三篇 14 章**
  - 基础篇（第 1–5 章）：物联网概述、体系架构、感知层、网络层、平台层
  - 技术篇（第 6–9 章）：软件开发、AIoT 与智能体、安全、协议与标准
  - 应用篇（第 10–14 章）：工业智造、智慧城市与车联网、农业、可信数据、IoT DC3 实战
- 体验：UI 美观、交互极佳、**全文搜索**、**三端响应式**、**图表点击放大**、便捷的多级目录。

## 2. 一句话方案

复用 `iot-dc3-online` 的 VitePress 技术栈与设计系统（品牌蓝 `#1296db` + 毛玻璃导航 + Hero 动效 + **现成的 `BookCover.vue` 立体书封组件**），新增一层「出版稿 → Web 稿」**转换脚本**（解决 Pandoc 图片属性 `{width=15cm}`、相对路径、缺失 frontmatter 三个不兼容点），用 VitePress 内置 **local search** + **medium-zoom** 实现搜索与图表放大，GitHub Pages + 自定义域 `book.dc3.site` 部署。

## 3. 设计文档索引

| 文档 | 内容 |
|---|---|
| [01-信息架构.md](./01-信息架构.md) | 内容来源、转换层（出版稿→Web 稿）、站点地图、URL 结构、目录（sidebar / outline）、上下章导航 |
| [02-视觉与交互.md](./02-视觉与交互.md) | 设计系统复用、首页、阅读页、搜索、图表放大、三端响应式 |
| [03-构建与部署.md](./03-构建与部署.md) | 目录结构、转换脚本设计、VitePress 配置、CI、CNAME / DNS、sitemap |

## 4. 已确认决策（Review 完成）

> 以下决策已与作者确认，作为实现的权威依据。

| 决策点 | 结论 |
|---|---|
| **视觉基调** | ✅ 复用 online 设计系统 + 阅读区「书卷气」优化 |
| **内容接入** | ✅ 独立转换脚本 `scripts/build_web.py`（不并入 book-builder，稳定后再议） |
| **图片托管** | ✅ `docs/public/figures/` 绝对路径 `/figures/...` |
| **搜索** | ✅ VitePress `local` search（MiniSearch，零外部依赖） |
| **图表放大** | ✅ `medium-zoom`（VitePress 官方文档站同款） |
| **多语言** | ✅ 单语言中文 |
| **目录命名** | ✅ `docs/` |
| **仓库地址** | ✅ `github.com/pnoker/iot-dc3-book`（editLink / socialLink 据此） |
| **首页动效** | ✅ 保留 online 粒子 + 波浪（仅首页 `home-hero-before`，不进阅读页） |
| **段落缩进** | ✅ 正文首行缩进 2em（中文书习惯；排除列表/代码块/图题/引用等非正文段落） |
| **卷首结构** | ✅ 作者简介 / 序 / 导读 / 目录 各自独立单页 |

## 5. 与 `iot-dc3-online` 的关系

- **复用**：VitePress + Vue3 技术栈；`style.css` 设计 token（品牌色、毛玻璃 nav、圆角、阴影）；**`BookCover.vue` 立体书封组件（中英双语 props，可直接迁移作首页主视觉）**；`deploy.yml` GitHub Pages CI 模式；Hero / glass nav / GlobalCursor 交互骨架；响应式断点（1280 / 960 / 640）。
- **不同**：book 站是**阅读型**站点（产品落地页 → 沉浸阅读）；**单语言**；内容来自**转换层**而非手写 md；新增**图表放大**与**章/篇扉页过渡**。

## 6. 三个必须知道的事实（来自源码核验）

1. **章节 md 用 Pandoc 属性语法**：`![图1-1 三次浪潮演进时间线示意](../figures/chapter-01/fig-01-01.png){width=15cm}` —— VitePress / markdown-it **不识别 `{width=15cm}`**，会原样泄漏到页面。这是接入的最大技术坑，必须由转换层处理（详见 [01-信息架构.md](./01-信息架构.md)）。
2. **节标题规范**：`## 1.1` / `### 1.1.1` —— 完美适配 VitePress 右侧 outline（自动从 H2/H3 生成「本页目录」），无需额外配置。
3. **online 已有 `BookCover.vue`**：一个超精细的 SVG 立体书封（星座点缀、蓝/青/绿/琥珀配色、双语），本就是为书站预留的封面组件，直接迁移即可，无需重做。

## 7. 实施路线图（概要，详见 [03-构建与部署.md](./03-构建与部署.md)）

1. **转换层 + docs 骨架**：写转换脚本，`output/` → `docs/`，本地 `pnpm dev` 可预览全书。
2. **VitePress 配置**：sidebar（篇/章两级）+ local search + outline + medium-zoom + 首页（迁移 `BookCover.vue`）。
3. **阅读体验打磨**：章扉页（`dividers/chapter-XX.png`）+ 篇页（`dividers/part-XX.png`）+ 图题样式 + 上下章导航。
4. **CI + 域名**：复用 `deploy.yml`，配 `public/CNAME = book.dc3.site`，DNS CNAME `book` → `<user>.github.io`，部署上线。
