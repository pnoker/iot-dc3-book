# iot-dc3-book

《从工业软件到 AI 智能体》在线书籍站点（https://book.dc3.site）——**手稿即终稿**：VitePress 直接以 `book/` 为根，手稿就是站点源，无导出中间层。中英双语（英文增量翻译中）。

## 用法

```bash
pnpm install        # Node 依赖（vitepress、yaml、nunjucks）

pnpm dev            # 本地开发（vitepress dev book，改手稿即时热更）
pnpm build          # 生产构建（vitepress build book + sitemap/feed/llms 后处理）
pnpm preview        # 预览 dist
```

## 内容结构

```
iot-dc3-book/
├── book/                      # VitePress 根：vitepress dev/build book
│   ├── WRITING_GUIDE.md       #   写作规范（唯一来源）
│   ├── .vitepress/            #   config.ts + seo.ts + theme/ + buildkit/（渲染期管线）
│   ├── config/                #   book/parts(-en)/style YAML
│   ├── manuscript/
│   │   ├── zh/                #   中文终稿：chapter-XX/X.Y.md + preface/ + appendix.md
│   │   └── en/                #   英文终稿：镜像结构，翻多少生成多少（README 有约定与进度）
│   ├── pages/{zh,en}/         #   结构页 stub（目录/篇/章，渲染期注入内容）
│   ├── figures/chapter-XX/    #   {fig-id}.html 图源 + {fig-id}.yaml 图注册表（spec + 双语 caption/labels）
│   ├── dividers/              #   章/篇扉页模板（web 内联渲染）
│   ├── assets/                #   cover.html / cover.png / logo.svg
│   └── public/                #   CNAME / robots / logo 等静态资源
└── scripts/                   # 构建后处理与工具（全部 Node）
    ├── enhance-sitemap.cjs    #   sitemap 补 lastmod
    ├── generate-feed.cjs      #   RSS feed
    ├── generate-llms-full.mjs #   llms-full.txt（LLM 索引）
    ├── gen-og-image.mjs       #   og:image 渲染（手动）
    └── figure-i18n.mjs        #   图内标注翻译桩（labels.en）
```

## 许可

内容版权归作者所有，详见站点[版权与许可](https://book.dc3.site/copyright)页。
