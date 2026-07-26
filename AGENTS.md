# AGENTS.md

本仓库的构建工具不依赖 Agent，但允许使用 Agent 辅助手稿写作、审校和维护。

## 修改手稿前

修改 `book/manuscript/` 前必须阅读并遵循：

- `book/WRITING_GUIDE.md`：全书写作规范的唯一来源；
- `book/config/book.yaml`：书名、署名和出版元数据；
- `book/config/parts.yaml`：篇章结构的唯一来源；
- `book/config/style.yaml`：图表字段、类型和配色的唯一来源。

不要在本文件复制写作规范或图表 schema，避免产生多个权威来源。

## 工作约束

- 只修改任务直接涉及的手稿、配置或构建代码，不顺带重写其他章节；
- 修改章节标题、编号或顺序后，检查目录、导读和跨章节引用；
- 修改 `book-figure` 时遵守 `style.yaml`，其中 `legend` 选填；
- 版本、标准、API 和性能数据先查一手资料；
- 完成后运行 `uv run book-builder build`，确认配置加载、手稿组装和图表扫描成功。
