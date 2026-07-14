# 2026-07-13 出版社投稿调研

本目录用于保存《物联网技术与实践：从万物互联到万物智联》面向出版社投稿前的存量书调研、竞品分析和投稿材料草稿。

## 文件说明

- `00-current-book-baseline.md`：当前书稿定位、目录、进度和投稿风险基准。
- `01-existing-books-summary.md`：机械工业出版社、电子工业出版社官网检索到的高相关存量书摘要。
- `02-competitive-analysis-and-direction.md`：重复度判断、差异化定位和可选调整方向。
- `03-submission-materials-draft.md`：按电子工业出版社网上投稿字段整理的可粘贴草稿，并兼容机械工业出版社投稿沟通。
- `04-supplemental-search-assessment.md`：按“AI 时代物联网系统构建”新定位补充检索后的判断。
- `extracted/existing-books-inventory.json`：结构化书目清单，保留 57 条检索结果及详情页抽取字段。
- `extracted/existing-books-inventory.csv`：同一批书目清单的表格版，便于下次用表格或脚本继续分析。
- `extracted/supplemental-ai-iot-search.json`、`extracted/supplemental-ai-iot-search.csv`：补充关键词检索结果。
- `raw/detail-pages/`：高相关图书详情页 HTML 原文，用于复核页面信息。
- `raw/cmpedu-chuban-index.html`、`raw/cmpedu-tougao.html`：机械工业出版社教育服务网出版/投稿入口页面。
- `raw/phei-contribution-index.html`：电子工业出版社网上投稿页面。

## 检索范围

- 站点：`https://www.cmpedu.com/index.htm`、`https://www.phei.com.cn/`。
- 关键词：`物联网技术与实践`、`物联网技术`、`AIoT`、`智能物联网`、`工业物联网`、`物联网平台`、`物联网应用开发`、`物联网安全`、`Spring AI`、`MCP 物联网`。
- 结果：机械工业出版社 26 条，电子工业出版社 31 条，共 57 条；其中 51 条补抓详情页。

## 快速结论

- 未在两站检索到与当前完整书名和副标题完全一致的图书。
- 存在明显相近书名：电子工业出版社《物联网技术与实践：基于ARM Cortex-M0技术》，但其出版时间为 2012 年，方向偏 ARM Cortex-M0 嵌入式实践。
- 存在大量“物联网技术导论/概论/应用/安全/开发实践”类图书，当前书名如果保持宽泛，容易被编辑误判为通用入门/教材型选题。
- 建议投稿时直接强调本书本来就是“面向 AI 时代的物联网系统构建与工业平台工程实践”，突出 IoT DC3、Spring AI、Tool-Calling、MCP、多协议接入和自然语言运维。
- 已按新定位补查“大模型、AI Agent、智能体、系统构建、工业物联网平台、智能运维、自然语言运维、MCP”等关键词，未发现新的高相关同类书；当前不需要继续在这两家出版社官网补充检索。

## 下次继续

- 先阅读 `02-competitive-analysis-and-direction.md` 选择书名和方向。
- 再在 `03-submission-materials-draft.md` 补齐作者个人信息、联系方式、最终交稿日期。
- 如需新增出版社，可把新检索结果追加到 `extracted/existing-books-inventory.json`，并在 `01-existing-books-summary.md` 增补摘要。
