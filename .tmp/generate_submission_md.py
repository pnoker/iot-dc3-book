from __future__ import annotations

from pathlib import Path
import re
import textwrap
import yaml

from core.workflow import BookProject


def clean(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.strip())


def indent_block(text: str, prefix: str = "  ") -> str:
    return "\n".join(prefix + line if line.strip() else line for line in text.strip().splitlines())


project = BookProject("config")
state = project.load_write_checkpoint_with_workers("book-1")
author_cfg = yaml.safe_load(Path("config/author.yaml").read_text(encoding="utf-8"))
profile = author_cfg["profile"]
book_text = Path("output/book.md").read_text(encoding="utf-8")
char_count = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", book_text))
image_count = len(re.findall(r"^!\[", book_text, flags=re.M))

content_intro = """
《AIoT 技术与实践：从物联网平台到智能体应用》是一部面向工程实践的物联网与 AIoT 技术图书。全书以“从设备接入到智能体应用”为主线，从物联网概念、体系架构、感知层、通信网络、平台层与数据处理等基础内容展开，进一步进入物联网软件开发、AIoT 与智能体应用、安全技术、协议与标准等核心技术主题，最后通过工业物联网、智慧城市、农业物联网、区块链融合以及 IoT DC3 项目实战，展示物联网技术在真实场景中的落地方法。

本书突出“基础能力 + AI 时代新范式 + 工程方法论”的结合：既讲清楚设备接入、协议适配、数据采集、边缘计算、平台治理等物联网基本功，也系统讨论大模型、Agent、Tool-Calling、RAG、MCP、自然语言运维等 AIoT 新能力如何进入物联网系统架构。书中以开源工业物联网平台 IoT DC3 为贯穿案例，帮助读者将抽象概念落实到平台架构、服务边界、数据链路、安全治理与项目交付中。
"""

reader_objects = """
主要读者包括：

1. 物联网、工业互联网、AIoT 方向的软件工程师、平台工程师、协议驱动开发人员；
2. 需要设计或评审物联网平台架构的架构师、技术负责人、解决方案工程师；
3. 正在从传统物联网平台升级到 AIoT / Agentic IoT 的研发团队和技术管理者；
4. 高校物联网工程、计算机、通信工程、人工智能交叉课程的高年级学生、研究生和教师；
5. 希望理解工业制造、智慧城市、农业、区块链等场景中物联网落地方法的技术读者。
"""

tech_need = """
物联网正在从“设备联网、数据展示”的初级阶段，进入“数据理解、智能决策、自动执行”的 AIoT 阶段。过去大量物联网图书以概念介绍、传感器和通信协议为主，或偏向单一行业应用，较少同时覆盖平台架构、云原生工程、AI Agent、MCP、Tool-Calling、工业级项目交付等新内容。与此同时，实际工程团队在项目中面临的难题并不是“是否知道某个协议名称”，而是如何把设备接入、数据治理、权限安全、边缘计算、AI 推理和业务闭环组织成可维护、可扩展、可交付的系统。

本选题的必要性在于：

- **技术代际变化明显**：大模型和 Agent 正在改变物联网的人机交互、运维方式和自动化能力，亟需一本把传统 IoT 基础与 AIoT 新范式贯通的技术书。
- **工程实践需求强**：企业落地物联网项目时，需要的不只是概念，而是架构拆分、协议选型、平台治理、安全策略、数据闭环和项目方法论。
- **国产开源实践可沉淀**：IoT DC3 作为长期迭代的开源工业物联网平台，覆盖多协议驱动、微服务架构、设备管理、数据采集和 AI 运维实践，适合作为贯穿案例。
- **教学与培训价值明确**：本书结构可支撑高校物联网工程、工业互联网、AIoT 实践课程，也适合企业内部技术培训。
"""

comparison = """
相较于传统同类书，本书的差异主要体现在：

| 维度 | 传统同类书常见特点 | 本书特点 |
|---|---|---|
| 技术范围 | 多聚焦概念、传感器、网络协议或单一应用场景 | 覆盖感知、网络、平台、软件开发、AI 融合、安全、协议标准和行业应用全链路 |
| AIoT 内容 | 多为补充章节或趋势介绍 | 将大模型、Agent、RAG、Tool-Calling、MCP、自然语言运维作为核心技术线索 |
| 工程落地 | 偏教学或概念讲解，项目架构细节较少 | 以 IoT DC3 为贯穿案例，强调微服务边界、协议驱动、数据链路、安全治理和交付方法 |
| 读者定位 | 偏入门教材或行业科普 | 面向工程师、架构师、技术负责人及高年级学生，兼顾系统性和工程判断 |
| 场景覆盖 | 单一行业或单一技术栈较多 | 覆盖工业制造、智慧城市、农业物联网、区块链融合、平台实战等多场景 |
"""

same_books_note = """
> 说明：投稿表单要求填写“出版社、印数、定价、作者及出版时间”。这些信息建议以出版社官网、国家版本数据中心、京东/当当页面或图书版权页核验后填写；在未核验前，不建议虚构印数和定价。下面先列出可作为同类书调研对象的方向与本地参考书线索，具体出版信息请投稿前补齐。

| 同类书方向/书名线索 | 出版社 | 印数 | 定价 | 作者 | 出版时间 | 与本书关系 |
|---|---|---:|---:|---|---|---|
| 物联网系统架构与边缘计算类图书 | 待核验 | 待核验 | 待核验 | 待核验 | 待核验 | 与本书的平台架构、边缘计算内容相关，但通常 AI Agent 与 MCP 内容较少 |
| 物联网云平台与大数据处理类图书 | 待核验 | 待核验 | 待核验 | 待核验 | 待核验 | 与本书的数据采集、平台层、时序数据处理相关，本书增加 AIoT 闭环与工程方法论 |
| 物联网 Python / 系统开发实践类图书 | 待核验 | 待核验 | 待核验 | 待核验 | 待核验 | 与本书软件开发实践相关，本书更强调工业平台、微服务和多协议驱动 |
| AIoT 开发实践类图书 | 待核验 | 待核验 | 待核验 | 待核验 | 待核验 | 与本书 AIoT 主题相关，本书以 IoT DC3 和 Agentic Center 作为贯穿工程案例 |
| NB-IoT、RFID、传感器等专项技术类图书 | 待核验 | 待核验 | 待核验 | 待核验 | 待核验 | 与本书感知层、网络层章节相关，本书定位更综合，覆盖平台和 AI 融合 |
"""

plan = f"""
目前书稿已形成可提交审读的完整初稿，约 16.7 万字，包含 14 章、234 个三级小节和 {image_count} 张图表。投稿后可根据出版社选题论证、编辑审读意见进行结构调整、篇幅压缩、配图精修、术语统一和参考文献规范化。

建议计划如下：

- **当前状态**：完整初稿已完成，可提交选题申报与编辑初审。
- **修订周期**：收到编辑意见后，预计 4～8 周可完成第一轮修订稿；如需增加配套代码、课件或案例素材，可另行排期。
- **合作者情况**：暂按作者独立编著申报；如出版社建议，可邀请工业物联网、云原生、AIoT 或高校物联网工程方向专家参与审阅或推荐。
- **拟审阅人方向**：建议邀请物联网平台架构师、工业互联网项目负责人、高校物联网工程/人工智能交叉方向教师、IoT DC3 社区核心用户或企业技术负责人进行技术审阅。
"""

outline_lines: list[str] = []
for part in state.parts:
    outline_lines.append(f"## {part.prefix}、{part.name}")
    outline_lines.append("")
    for chapter in part.chapters:
        outline_lines.append(f"### 第{chapter.id}章 {chapter.title}")
        if chapter.summary:
            summary = " ".join(chapter.summary.strip().split())
            outline_lines.append(f"- 章节要点：{summary}")
        groups: dict[str, list[object]] = {}
        group_order: list[str] = []
        for sec in chapter.sections:
            key = sec.id.rsplit('.', 1)[0]
            parent = sec.parent_title or key
            group_key = f"{key} {parent}"
            if group_key not in groups:
                groups[group_key] = []
                group_order.append(group_key)
            groups[group_key].append(sec)
        for group_key in group_order:
            outline_lines.append(f"- {group_key}")
            for sec in groups[group_key]:
                outline_lines.append(f"  - {sec.id} {sec.title}")
        outline_lines.append("")
outline = "\n".join(outline_lines).strip()

important_refs = """
重要参考资料方向包括：

1. 物联网总体架构、边缘计算、雾计算、云平台与大数据处理相关图书和论文；
2. 感知层技术资料，包括 RFID、传感器、北斗应用、网络化感知等；
3. 通信与网络协议资料，包括 NB-IoT、MQTT、CoAP、LwM2M、OPC UA、BLE、HTTP/HTTPS 等；
4. 物联网安全资料，包括设备身份、通信安全、数据安全、隐私保护、TLS、JWT、RBAC/ABAC 等；
5. AIoT 与大模型资料，包括 Spring AI、RAG、Tool-Calling、Agent、MCP、模型私有化部署等；
6. IoT DC3 官方中文文档及源码实践，涵盖架构、驱动、模块、开发、运维、AI、自动化等内容；
7. 工业物联网、智慧城市、农业物联网、区块链融合等行业应用报告与案例资料。
"""

md = f"""# 电子工业出版社网上投稿表单填写稿

> 用途：复制到“作译者服务 > 网上投稿”页面对应字段。  
> 注意：涉及真实姓名、性别、出生年月、学历、单位、联系方式等个人信息的字段，请以合同/身份证件/单位信息为准替换。本文不虚构未确认的私人信息和同类书销售数据。

## 一、个人资料

| 字段 | 建议填写内容 |
|---|---|
| 姓名 | {profile.get('name', state.author)} |
| 性别 | 【请填写：男 / 女】 |
| 出生年月 | 【请填写】 |
| 职称或职务 | {profile.get('title', '物联网平台架构师 · AIoT 实践者')} |
| 学历 | 【请填写】 |
| 研究方向或教学科目 | {'、'.join(profile.get('expertise', []))} |
| 单位 | 【请填写】 |
| E-mail 地址 | 【请填写】 |
| 通信地址 | 【请填写】 |
| 邮政编码 | 【请填写】 |
| 电话 | 【请填写】 |

## 二、个人简历

{clean(profile.get('bio', '【请填写个人简历】'))}

项目经历补充：

- 开源项目：{profile.get('project', 'IoT DC3')}
- 项目地址：{profile.get('project_url', 'https://gitee.com/pnoker/iot-dc3')}
- 项目简介：{clean(profile.get('project_description', ''))}

## 三、申报资料

| 字段 | 建议填写内容 |
|---|---|
| 申报选题名称 | 《{state.book_title}：{state.book_subtitle}》 |
| 预计交稿时间 | 已完成可审读初稿；收到编辑意见后预计 4～8 周内提交修订稿/定稿（可按出版社流程调整） |
| 选题板块划分 | 建议选择：计算机技术 / 物联网 / 人工智能与大数据 / 工业互联网 / 通信与网络（以网站下拉选项为准） |

## 四、内容简介与读者对象

### 内容简介

{clean(content_intro)}

### 读者对象

{clean(reader_objects)}

## 五、引进版图书原著相关内容

本书为原创中文技术图书，不属于引进版图书。以下字段可填“不适用”。

| 字段 | 填写内容 |
|---|---|
| 书名 | 不适用 |
| 作者 | 不适用 |
| 出版社 | 不适用 |
| 出版年月 | 不适用 |
| 页码 | 不适用 |
| ISBN号 | 不适用 |

## 六、该选题的特色技术背景和必要性

{clean(tech_need)}

## 七、与同类书比较

### 已出版同类书调研表

{clean(same_books_note)}

### 本书与同类书比较

{clean(comparison)}

## 八、编著计划

{clean(plan)}

## 九、章节目录

{outline}

## 十、编著此书的重要参考资料

{clean(important_refs)}

## 十一、投稿前建议补充核验项

- 【必填】真实姓名、性别、出生年月、学历、单位、邮箱、电话、通信地址、邮政编码。
- 【建议】根据出版社网站实际下拉选项，确认“选题板块划分”的最终分类。
- 【建议】同类书表格中的出版社、印数、定价、作者、出版时间，请以出版社官网、国家版本数据中心、京东/当当页面或图书版权页核验后补齐。
- 【建议】如有可公开列出的论文、专利、项目获奖、课程建设、企业案例或开源社区数据，可补充到“个人简历”。
- 【建议】投稿附件可同时准备：`output/book.docx`、`output/book.md`、图表目录 `output/figures/`、一页版选题说明。
"""

out = Path("output/submission-form.md")
out.write_text(md, encoding="utf-8")
print(out)
