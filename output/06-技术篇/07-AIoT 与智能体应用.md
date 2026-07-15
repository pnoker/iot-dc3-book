# 第7章 AIoT 与智能体应用

## 7.1 AIoT 技术全景

### 7.1.1 AIoT 的定义与演进脉络

大屏弹出红色告警——某台冷却泵振动值越限。操作员手动拉起趋势图，翻看设备档案，比对维修日志，经过一轮人工判断后才能区分偶发抖动和轴承磨损前兆。数据看得见，决策靠人猜。物联网解决了“连接”的问题——传感器、PLC、RFID 源源不断地把数据上传到平台。但连接的终点仍常常是人类操作员：数据呈现在仪表盘上，分析靠经验，决策靠判断，执行靠手动点击。

AIoT（人工智能物联网，Artificial Intelligence of Things）打破了这种割裂。它把人工智能，尤其是大语言模型和多模态模型，嵌入到物联网“采集—分析—决策—执行”闭环中，让机器不仅看得见数据，还能理解语义、推理因果、自动操作。一条线概括：IoT 让世界可感知，AI 让感知可行动。

IoT DC3 平台的设计抓住了这条主线。AI 的所有动作最终都走平台真实 API，经网关注入主体上下文，再由鉴权中心做 RBAC 权限校验与租户隔离——模型拿不到比对应账号更多的权限（资料：[S6]）。这意味着 AIoT 不是在物联网之上“叠”一层智能，而是将智能注入原有数据管道，让 AI 成为操作链路上可信的执行者。

#### 1. 演进三阶段：连接、智能分析、自主决策

AIoT 的成熟大致经历了三个阶段，每个阶段的技术特征和智能化程度有明显差异。下面用示意图展示作者整理的演进脉络。

![图7-1 AIoT 演进阶段示意](../figures/chapter-07/fig-07-01.png){width=15cm}

*图7-1 AIoT 从连接到自主决策的演进示意。第一阶段设备上网，数据汇聚，人看仪表盘做判断；第二阶段 LLM 理解语义，通过工具调用查设备、写位号、下命令，人机协作；第三阶段 Agent 自主监测、诊断、规划、执行，人类从操作员变为监督员。驱动因素包括算力下沉、大模型突破和边缘智能普及。*

**第一阶段：连接与数据采集。** 主题是“把设备连起来”。大型物联网平台重点解决设备注册、协议适配、数据采集与存储。平台像一条数据管道：传感器值经过网关、流处理引擎，存入时序数据库，最终展现在仪表盘上供人查看。智能非常浅——大多是基于阈值的告警规则引擎（诸如温度越限触发告警）。规则引擎确定性强，但无法处理模糊、多变、语义丰富的场景。运维人员需要频繁调整阈值来适应工况变化，误报和漏报一直是痛点。这个阶段的核心交付物是可读、可查的数据，而非可执行的智能。

**第二阶段：智能分析与人机协作。** 边缘计算和轻量级机器学习模型开始落地。异常检测、预测性维护等算法被引入。模型跑在独立推理服务上，输出结果喂给告警系统或大屏。近年来，主流大语言模型具备了可靠的多步推理和工具调用能力，使物联网系统第一次能像人类一样“读懂”设备手册，然后根据指令去操作一台设备。这种自然语言操控物联网的能力逐渐从实验走向可用。IoT DC3 的 Agentic Center 正是在这个背景下诞生的——它把一个 OpenAI API 兼容的大模型接到设备、位号、数据与命令上，用户用自然语言提问，模型按需调用平台内置工具去读元数据、查实时值，甚至在受控授权下触发设备读写。与第一阶段的核心区别在于：模型不再是旁观者，而是操作链路上的参与者。

**第三阶段：自主决策与闭环控制（正在成形）。** 模型不再等待人类发问，而是持续监测数据流，主动发现异常、诊断根因、提出策略，并在人类确认或预设规则允许的情况下自动执行。该阶段的典型特征包括：定时健康报告自动生成（如每日清晨输出前一晚的设备离线汇总和趋势异常设备建议）、多模型按任务复杂度路由（简单查询走轻量模型，复杂诊断走更强的模型，本地敏感查询走私有部署），以及外部 AI Agent 通过 MCP 协议自由接入平台工具集。人类角色的转变最深刻：从操作员变为监督员，只在关键决策节点介入确认。IoT DC3 已内置“高风险动作确认”机制，例如设备写操作需要二次确认方可执行。

#### 2. 核心驱动力：算力与模型的共生

从第二阶段向第三阶段演进，背后有两条并行的驱动力。

**第一条：算力下沉。** 物联网的经典痛点是云端推理延迟高、带宽贵、隐私风险大。合理的工程分工是“云侧训练、边缘推理、端侧响应”：云上用全量历史数据训练模型，下发到边缘做低延迟推理，端侧只做最后一脚的快速响应。以嵌入式 AI 芯片为代表的边缘计算设备，已能在有限功耗下运行轻量级 LLM 或视觉模型，使得边缘端部署大语言模型成为工程可行。算力下沉的直接收益是推理时延显著降低，且敏感数据不必离开本地网络。

**第二条：模型能力的跃迁。** 大语言模型近年完成了从“文本对话”到“工具调用”的能力跃迁。传统物联网智能依赖规则和分类回归模型，而今天的 LLM 能根据“把二号线的进料阀调到较低开度”这样的自然语言指令，推理出需要调哪个 API、传什么参数、甚至做边界校验。这种能力与物联网“指令密集”的特性天然匹配。IoT DC3 的处理方式很务实：通过 Spring AI 将工具调用变成普通的 Java 方法调用，让模型的理解能力与平台已有的业务逻辑无缝衔接。模型无需感知底层协议差异（Modbus、OPC UA、MQTT），因为这些差异已被平台的设备抽象层屏蔽。

这两条驱动力共同指向一个结论：AIoT 已经从概念走向工程落地。接下来的小节会逐一拆解大模型在物联网中的具体角色（7.1.2）、Agent 如何实现自主决策（7.1.3）、以及 RAG、Tool-Calling、MCP 等让模型伸手够到物理世界的关键技术（7.1.4、7.1.5）。

### 7.1.2 大模型在物联网中的角色：从感知到认知

规则引擎作为传统物联网的核心分析手段，已运行多年：温度超阈值就告警，离线就通知。这套机制边界清楚——只能处理明确定义的离散规则。当运维人员面对“二号泵房温度比昨天同期高了5度，但负载是下降的”这类复合判断时，规则引擎只能输出“温度超限”四个字。它无法理解“比昨天同期”的语义，也不能推理“负载下降时温度异常上升”这种因果关联。

大模型介入后，这个上限被打破了。模型不只是识别“温度86℃”这个数字，还能关联上下文——季节、负载、历史趋势、维修记录——然后做出“这不是正常波动，可能是冷却泵效率下降”的判断。从**数值判断到语义推理**的跃迁，是大模型赋予物联网的核心价值：让机器从只懂“检测”进化到能够“理解”。这种改变并非彻底替换规则引擎，而是在其之上叠加一层认知能力——规则引擎继续处理秒级响应和离散事件，大模型处理那些需要理解上下文、模糊匹配和因果推断的任务。

#### 1. 从规则到语义：自然语言指令穿透设备层

第一个显著变化是设备控制方式。传统路径是：打开设备列表→找到目标设备→展开属性→输入值→点击写入，多步操作、深层嵌套。大模型将其压缩成一句话：“关掉一楼走廊灯”或“2号反应釜温度调到85度保持30分钟”。平台收到指令后，大模型完成意图识别（“关灯”对应某个可控开关测点）、参数抽取（“85度”对应温度设定值）、动作映射（找到正确的设备命令接口），最终触发真实设备写操作。

IoT DC3 的 Agentic Center 正是按这个思路设计的。它通过 Spring AI 的 `@Tool` 注解，把设备查询、位号读写、命令执行暴露给大模型（资料：[S11]）。当操作员说“读取锅炉温度和风机转速”，Agentic Center 依次调用两次工具：一次查锅炉温度测点，一次查风机转速测点。工具走平台真实 API，认证上下文由 Spring Security 过滤器链带入，确保大模型读取的是当前具身数据，而非训练集里的记忆。

这里有一个工程边界必须明确：自然语言指令适用于操作意图清晰、安全风险可控的场景。对于操作人员初次发出的设备控制指令，Agentic Center 要求用户二次确认后才发送到设备——这个设计不是为了保护模型，而是为了让人始终保持在决策环内。

#### 2. 多模态融合：不止是文本对话

工业场景的输入不限于文本和数字。摄像头拍到设备面板异常指示灯闪烁，运维人员拍了张照片发到群聊问“这是什么意思？”——传统平台无法处理这种输入。多模态大模型（例如 OpenAI 的 GPT-4o、Anthropic 的 Claude 4 等主流模型）可以同时接受图像和文本输入：照片里的闪烁灯模式、仪表指针位置、电线烧焦的颜色，都能纳入推理范围。

但职责边界需要划清：大模型擅长语义推理，不负责毫秒级实时控制。电机紧急刹车、继电器跳闸这类响应，仍由硬件控制器和边缘实时系统承担。大模型的注意力放在认知层——帮运维人员理解“为什么出了这个异常”“下一步该做什么”。这与消防系统的分工类似：喷淋头由温度传感器即时触发，但“全楼是否疏散、通知哪几个部门”的判断，托付给懂上下文的决策者。大模型扮演的正是这个决策辅助角色，工作重点是减少人的认知负担而非取代硬件控制回路。

#### 3. 从描述到推理：自动生成运维策略

规则引擎检测到告警只能说“温度超过85℃”。大模型能做更多：拉取测点过去7天的趋势，比对同期数据，查阅维修日志，输出一段有逻辑的诊断——“这次升温速度是平日的2倍，结合最近两次停机记录，可能是冷却泵轴承磨损导致效率下降。建议30分钟内安排停炉检查，重点查冷却泵电流和出口压力。”

这是从**描述性分析**（“现在温度是多少”）到**诊断性分析**（“为什么温度高”），再到**建议性分析**（“接下来该怎么办”）的跃迁。支撑这一跃迁的关键基础是工具调用能力——大模型本身不具备读取实时数据、查询维修日志的权限，但通过 Agentic Center 内置的10个 `@Tool` 工具（覆盖设备、驱动、位号、事件等对象），模型可以在推理过程中按需调用这些工具获取必要信息，再综合判断输出建议。

**表7-1 大模型在物联网中的典型应用场景对比**

| 场景 | 传统规则引擎处理方式 | 大模型介入后的处理方式 |
|------|---------------------|------------------------|
| 设备控制 | 通过仪表盘手动点击或预设写值指令 | 自然语言指令自动解析意图，调用工具执行、用户确认后写入 |
| 告警触发 | 固定阈值判断，触发后发送模板化通知 | 结合上下文推理根因，生成诊断建议和处理步骤 |
| 异常分析 | 显示超限数据和基础统计 | 梳理趋势、关联日志，生成自然语言解释与应对策略 |
| 运维策略 | 人工根据历史数据报告制定 | 模型综合多种数据源，主动给出操作建议和报告 |

大模型在物联网中的角色可以这样收束：它补上了长期缺失的认知层。传感器采集海量数据，规则引擎做快速判决，但“理解上下文、生成建议、与人对话”在过去一直空缺。大模型正好填补这块空白，让物联网从只能被动感知，进化为能够主动认知，同时不取代原有的实时控制逻辑。下一节将讨论支撑这种认知能力的执行体——Agent架构。

### 7.1.3 Agent 架构：让物联网自主决策

规则引擎能处理预设的逻辑判断，大模型能理解模糊的自然语言。但“排查2号线的温度异常”这类任务，需要的既不是单步告警，也不是一次推理——它要求像老手一样，先查设备状态，再看历史趋势，对比相邻位号，最后给出根因。这串动作有顺序、有依赖、有异常分支，单靠一条规则或一次模型调用做不到。Agent 架构就是为这类“多步决策”场景设计的。

#### 1. 什么是 Agent：不止理解，还能自主执行

Agent 是一个能**自主感知环境、做出决策、执行动作**的软件实体。在 AIoT 语境下，它的组成可以概括为：

**Agent = 大模型（LLM） + 记忆（Memory） + 规划（Planning） + 工具调用（Tool Calling）**

- **LLM** 是推理引擎，负责理解指令、判断下一步做什么。
- **记忆** 让 Agent 记住对话上下文、之前的查询结果和操作历史。IoT DC3 通过会话持久化和消息历史实现，确保多轮对话中状态不丢失。
- **规划** 让 Agent 把“排查温度异常”这种模糊需求拆解成步骤：先查设备状态，再看历史趋势，最后对比相邻位号。
- **工具调用** 是 Agent 与实际系统的连接器。在 IoT DC3 的 Agentic Center 中，它表现为 `DeviceTool`、`PointValueTool` 等带 `@Tool` 注解的 Spring Bean，每个方法封装了平台的真实 API（查询设备、读写位号、下发命令）。

AutoGPT 和 BabyAGI 等早期开源项目展示了 Agent 架构在自主任务分解中的可行性，它们依赖 LLM 的推理能力，通过循环调用工具完成原本需要人工多步操作的任务。这些项目的共性正是上述四个组件的组合。

#### 2. ReAct 模式：推理与行动的交替循环

Agent 完成多步任务的核心机制是 **ReAct**（Reasoning + Acting，推理 + 行动），最早由 Yao et al. (2023) 提出。它让模型交替输出思考过程和具体动作，形成一个持续的闭环。

一个典型的 ReAct 循环在物联网场景中可概括为：

1. **用户输入** → Agent 解析目标
2. **思考（Thought）**：Agent 判断“当前需要哪些信息？用什么工具去获取？”
3. **行动（Action）**：调用具体工具，例如查询设备状态
4. **观察（Observation）**：工具返回结果，可能是数据、状态或错误信息
5. **返回思考**：根据观察结果，再决定下一步行动
6. ……循环直到满足完成条件
7. **最终回答**：输出结果给用户

这个循环赋予了 Agent 容错和自适应能力。例如第一步调用查询工具返回空值，Agent 不会卡住，而会在思考阶段判断“可能需要调整查询参数”，然后再次尝试。

![图7-3 ReAct 循环在物联网 Agent 中的工作示意](../figures/chapter-07/fig-7-3.png){width=15cm}

*图7-3  ReAct 循环在物联网 Agent 中的工作示意，展示自然语言指令如何通过推理-行动-观察循环完成多步任务。*

#### 3. 示意案例：Agent 自主排查“1号泵房离线”

以下是一个示意场景，展示 Agent 通过 ReAct 循环处理“1号泵房离线告警”的排查过程。场景中的工具名称与 IoT DC3 的 Agentic Center 内部接口一致，但具体执行路径和数据输出为示意构造，不指向任何真实项目。

**目标**：处理“1号泵房离线告警”

1. **思考**：Agent 判断需要先确认设备真实状态，再查最近维护记录，最后决定能否远程恢复。
2. **行动**：调用 `DeviceTool.getStatus()`，返回“设备当前状态：离线”。
3. **观察**：工具确认离线，排除误报。Agent 继续判断：“离线原因是什么？”
4. **行动**：调用 `EventTool.getRecentByDevice()`，返回“2小时前触发离线告警，原因记录为空”。
5. **思考**：无明确原因，Agent 决定尝试远程重启。但写操作为高风险动作，系统要求人工确认。
6. **行动**：Agent 输出“预备执行重启指令，请确认”。用户确认后，调用 `CommandTool.sendCommand()` 发送重启指令。
7. **最终输出**：返回“已执行重启操作，当前状态恢复”。

整个流程中，Agent 完成了原本需要工程师逐步判断和操作的还原分析工作。如果重启失败，Agent 可以继续思考“联系维护人员”或“切换备用泵”，而不需要等待人工介入重新规划。

#### 4. Agent 的边界：自主不是无限自由

说清 Agent 的能力，也得说清它的约束。物理世界的误操作代价很高——误关一台生产设备，可能造成整条产线停工。完全的“无人值守”在大多数工业场景中并不现实。

IoT DC3 在这个问题上做了分层授权：工具调用走 OAuth 2.1 + 租户隔离 + 工具白名单，Agent 拿到的权限等同于当前登录用户。系统根据风险分级决定哪些操作需要人工确认——对写设备寄存器、重启驱动这类高风险动作，Agent 会主动请求确认，确认后才能执行。Agent 的思考和操作轨迹全程可追溯，每一步的决策逻辑和工具调用记录都保留在会话历史中。

从更广的视角看，Agent 在物联网中不是取代人，而是承接那些重复、繁琐、需要多步推理的工作——让人的精力集中在异常判断和边界决策上。ReAct 模式提供的不是万能方案，而是一个可观察、可干预、可兜底的工作框架。

---

**检查清单：Agent 架构落地要点**

| 维度 | 要点 | 说明 |
|---|---|---|
| 推理引擎 | LLM 选择 | 需支撑函数调用（Function Calling），支持多轮推理 |
| 记忆管理 | 会话持久化 | 跟踪历史操作，避免重复执行 |
| 规划能力 | 任务分解 | 能将模糊目标拆成子步骤，按顺序或并行执行 |
| 工具接入 | 接口封装 | 每个工具方法应对应单一职责，返回值结构统一 |
| 高风险控制 | 人工确认 | 写操作、重启、命令执行需设置审批环节 |
| 可审计 | 日志与追溯 | 记录每个思考→行动→观察的完整路径 |

### 7.1.4 RAG 与 Tool-Calling：扩展知识边界

大模型接入物联网运维，很快就会撞上两个实打实的短板。第一个是知识边界：模型训练完的那一刻，它知道的就已经过时了——昨晚上线的变频器、刚刚更新的寄存器映射表、这个季度才改的标准化作业流程，它一概不知。第二个是行动边界：模型再聪明，也只能输出文本，没法直接往总线上发指令。操作员问“重启3号泵”，它只能回答“请登录平台，在设备管理界面找到3号泵，点击重启按钮”。RAG（Retrieval-Augmented Generation，检索增强生成）和 Tool-Calling（工具调用）正好各自解决一个缺口：前者让模型带着实时资料回答问题，后者让模型能真正操作设备。

#### 1. RAG：让模型不再“凭空回答”

RAG 的核心思路很直白：模型在生成回复之前，先从外部知识库检索最相关的信息片段作为上下文，然后再生成。这样一来，大语言模型不必靠训练参数里封存的记忆来作答——那些记忆可能已经过期，甚至根本没存过你系统里的专有设备。在物联网运维场景中，RAG 的检索对象通常包括设备安装手册、Modbus 寄存器映射表、历史故障记录、标准化作业流程（SOP）、驱动程序升级日志等。

一个典型的检索流程是：操作员在对话中问“这台温控器报E4故障该做什么”，系统先把这个查询转换成向量表示，在文档向量库中检索出最相关的几篇故障排除记录，连同原始问题一起发给大语言模型。大语言模型根据检索到的内容，生成具体的排查步骤，并列出需要检查的位号。在 IoT DC3 的 Agentic Center 中，RAG 被用于智能告警分析：当设备触发离线告警时，Agent 自动检索知识库中同类设备的维修记录、驱动程序重启方案，以及该设备最近的变更操作日志，然后把根因分析和建议动作一并输出给操作员（资料：[S4]）。相比传统规则引擎只推送“设备离线”四个字，这种回复的信息密度和实用性都高得多。

RAG 的工程难点在于检索质量。知识库里混入过时的维护记录，模型就可能基于错误信息给出建议；向量化分块时把 SOP 的步骤 A 和步骤 D 切到了同一个块，模型拿到的上下文就是混乱的。实践中通常引入两个工程手段：文档版本管理和检索结果重排序。新部署的设备文档必须标注版本号，过期的文档从向量库中移除或降权；检索到的候选条目再用轻量级排序模型（如 Cohere Rerank 或 BGE Reranker）重排一次，确保最相关的文档优先进入大语言模型上下文窗口。

用 LangChain 实现 RAG 的示意代码如下：

```python
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA

# 加载运维知识库（设备文档、SOP）
vectorstore = FAISS.load_local("iot_knowledge_base", OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o", temperature=0),
    chain_type="stuff",
    retriever=retriever
)

response = qa_chain.run("二号除尘风机持续高温告警，该怎么处理？")
print(response)
# 输出：检索到2024-08的维护记录，第一步检查变频器散热风道是否堵塞。
```

这个示意代码假设你已经有了一个本地向量库，里面存储了设备的运维文档和 SOP。实际生产环境中，还需要考虑文档的增量更新、向量数据库的性能，以及不同租户间知识库的隔离。

#### 2. Tool-Calling：让模型从“说”变成“做”

Tool-Calling 让大语言模型在生成回复时输出结构化的函数调用请求——指定函数名和参数，而不是自然语言。应用层拦截这个请求，执行对应的业务逻辑，再把执行结果返回给模型，最终由模型组织成自然语言回复。在 IoT DC3 的 Agentic Center 中，10 个 `@Tool` 注解的工具类正是为此设计的（资料：[S1]）：`DeviceTool` 查设备状态，`PointValueTool` 读写位号，`CommandTool` 下发控制指令。每个工具在 Spring AI 框架中就是一个带 `@Tool` 注解的 Java Bean 方法，类型安全、租户感知，认证上下文与平台其他请求走同一套 Security 过滤器链（资料：[S5]）。

一个典型的 Tool-Calling 示意（基于 Spring AI）：

```java
@Tool(description = "创建一条新的告警规则")
public String createAlarmRule(
    @ToolParam(description = "规则名称，如'温度超限'") String ruleName,
    @ToolParam(description = "触发条件表达式，如'pointValue>100'") String condition,
    @ToolParam(description = "通知方式：sms/email/webhook") String notifyMethod
) {
    return alarmRuleService.create(ruleName, condition, notifyMethod);
}
```

操作员说“给1号线温度点位加一个超过90度就发短信的告警规则”，大语言模型解析意图后，自动调用 `createAlarmRule` 方法，填入 `ruleName="1号线温度超限"`、`condition="line01_temp>90"`、`notifyMethod="sms"`。方法执行后返回规则 ID，模型再将结果组织成“已创建规则”。整个过程省去了操作员在多个界面间跳转配置的环节。

Tool-Calling 的安全风险值得特别关注。如果模型误读意图——比如把“暂停3号泵”理解成“关闭3号泵”——一次错误调用就可能造成设备损坏。IoT DC3 对此引入了高风险确认机制：所有写操作类工具（如 `CommandTool`）在执行前，Agent 先返回确认弹窗，操作员点击确认后指令才会真正发出（资料：[S4]）。这个机制在工具函数执行前的拦截层实现，不会影响只读工具的调用效率。

#### 3. 结合使用：先检索后执行

RAG 解决的是模型“知不知道”的问题，Tool-Calling 解决的是模型“能不能做”的问题。在复杂运维场景中，两者常常串联使用：先通过 RAG 检索出正确的操作步骤或参数模板，再由 Tool-Calling 执行具体操作。

联合工作流的典型对话（假设场景）：

**操作员**：“二号车间的除湿机频繁跳闸，按标准流程排查处理。”  
**Agent 执行过程**：

1. **RAG 检索**：从知识库命中“DC-DEHUM-02 重复跳闸 SOP V2”
2. **步骤1**：查当前状态 → 调用 `PointValueTool` 读取 `dehum02/status` 和 `dehum02/fault_code`
3. **步骤2**：结合 SOP 分析 `fault_code=0xE3` 表示“压缩机过流”，输出初步诊断
4. **步骤3**：建议动作：重启并记录电流峰值；调用 `CommandTool` 下发重启指令
5. **结果**：“已执行重启操作，初步判断原因为压缩机瞬时过流，建议安排现场巡检确认。”

没有 RAG，模型不认识 `0xE3` 这个故障码，也无从知道 SOP 里写了什么；没有 Tool-Calling，模型只能给出“建议重启”这样的文本建议，操作员还得手动跳转多个界面才能执行。两者结合之后，大语言模型才真正从“能说的顾问”变成“能动手值班员”。

![图7-4 RAG + Tool-Calling 联合工作流](../figures/chapter-07/fig-7-4.png){width=15cm}

*图7-4 RAG + Tool-Calling 联合工作流图。操作员发起任务后，LLM 首先通过 RAG 检索设备 SOP 文档，获取操作步骤；随后按步骤依次调用 Tool-Calling 执行具体设备操作，直至任务完成。*

RAG 与 Tool-Calling 的组合，使得大语言模型在物联网运维中既不会“凭空作答”，也不会“只能动口”。两个机制构成了智能化运维的操作基础，为后续 Agent 系统实现自主规划与执行提供了双重保障。下一节将把视角从单个工具调用拉升到系统集成层面，看看这些能力如何通过标准协议暴露给外部 AI Agent。

### 7.1.5 MCP 协议：跨系统交互标准

RAG 补上了知识滞后，Tool-Calling 让模型能动手。但当一个物联网平台想把几十种设备驱动、数据库、告警服务、报表生成器全部暴露给外部 AI Agent 时，每个工具单独写一套 API 定义、鉴权方式和版本管理，工程成本会迅速失控。MCP（Model Context Protocol，模型上下文协议）正是在这个背景下出现的——它为模型与外部系统之间的通信定义了一套标准化接口，让部署和维护从“逐个适配”变成“统一接入”。

#### 1. MCP 是什么

MCP 是一个开放协议，核心思路是将每个外部能力封装成一个 Resource。每个 Resource 有自己的标识、描述和输入输出定义。模型通过一个标准端点发送 JSON-RPC 2.0 请求来调用这些 Resource。对模型而言，无论后端连接的是 Modbus 驱动、PostgreSQL 查询还是 Slack 告警推送，都只是不同的 Resource——调用方式完全一致。

在 IoT DC3 中，MCP 的定位是“把平台工具安全暴露给外部 AI Agent”。它不同于 Agentic Center（面向人类操作员的对话框），而是专为外部编排系统或自主 Agent 设计的机器接口。DC3 的网关在 `POST /mcp` 上提供了 MCP Resource Server，工具目录由四个中心服务（Manager、Data、Auth、Agentic）的 OpenAPI 定义自动聚合而成，数量可观。这些 Resource 的调用走基于 OAuth 的鉴权，外加工具白名单和风险分级——模型只能调用被允许且风险等级可接受的那些工具（资料：DC3 AI 概览）。

#### 2. 在物联网中，MCP 封装了什么

物联网系统的后端能力可以归为几大类，每类都可以被 MCP Resource 封装：

- **设备驱动操作**：读取寄存器、写入参数、启停设备。对应 DC3 中的 DeviceTool、DriverTool、CommandTool 等内建工具。
- **数据查询**：实时值、历史趋势、聚合统计。对应 PointValueTool。
- **元数据管理**：设备列表、位号定义、租户信息。对应 TenantTool、ProfileTool、PointTool。
- **告警与事件**：查询当前告警、确认告警、回溯原因。对应 EventTool。
- **运维辅助**：日志搜索、文档检索（RAG 的来源之一）。

通过 MCP，外部 Agent 不需要知道每个工具的具体 URL、鉴权 token 的格式、请求体的拼写规则——它只需知道一个 MCP 端点地址，通过 `tools/list` 发现接口获取所有可用 Resource 的描述，然后按需调用。这意味着工具目录的变更对 Agent 几乎是透明的。

#### 3. 对比传统 REST/MQTT：跨系统接口的工程权衡

传统物联网平台对外暴露能力有两种常见方式：预设 REST API 文档，或者通过 MQTT 主题订阅/发布。这两种方式在 Agent 场景下都有明显缺陷。

**REST API 的问题在于静态绑定**。API 文档由人工维护，一旦新增或变更工具，Agent 需要等待文档更新、重新加载，或者硬编码调用路径。MCP 通过 OpenAPI 自动聚合实现了动态发现：服务启动时自动扫描所有 `@Tool` 注解的方法，生成 Resource 列表，Agent 在运行时通过 `tools/list` 即可获取最新目录。DC3 的 MCP 网关正是利用四个中心的 OpenAPI 定义自动聚合，无需手动注册（资料：DC3 AI 概览）。

**MQTT 的问题在于安全粒度粗糙**。一个客户端可以订阅任意主题，权限控制是主题级别的，难以做到按操作、按参数、按租户隔离。MCP 的请求走 HTTP，每个调用都经过基于 OAuth 的认证，网关内置工具白名单和风险分级机制——比如“写寄存器”这种高风险操作，需要更高等级授权，甚至触发人工确认（资料：DC3 AI 概览）。这种细粒度控制对物联网至关重要，因为设备操作一旦失误可能影响生产安全。

此外，MCP 天生支持工具链组合：Agent 可以在一次会话中依次调用多个 Resource，而不需要为每个协议建立独立的连接、处理不同的消息边界。对于“查设备 A 温度→判断异常→读历史趋势→调低制冷设定值”这种多步运维任务，能显著减少编排复杂度。这三类方式的工程权衡对比见表 7-2。

| 比较维度 | REST API | MQTT | MCP |
|---------|----------|------|-----|
| 接口发现 | 人工维护文档，静态绑定 | 无内置发现机制 | 动态发现，服务启动时自动注册 |
| 安全粒度 | 基于 URL 和 token，可细粒度但需代码实现 | 主题级权限，难以按参数隔离 | 基于 OAuth + 白名单 + 风险分级，可做到操作级控制 |
| 风险控制 | 需额外网关或日志审计 | 无原生机制 | 内建风险分级引擎，高风险操作可触发人工确认 |
| 工具链编排 | 需要为每个 API 设计调用逻辑 | 需处理消息边界和顺序 | 同一次会话中自然编排，基于 JSON-RPC 2.0 |
| Agent 适配成本 | 高（需按文档逐个适配） | 中（需实现订阅/发布逻辑） | 低（只需连接一个端点，通过发现接口获取工具列表） |

#### 4. MCP 架构示意

下面展示 MCP 在物联网平台中的典型部署架构，重点体现外部 Agent 通过单一 MCP 端点访问多个后端服务的方式。

![图7-4 MCP 在物联网平台中的架构示意](../figures/chapter-07/fig-07-04.png){width=15cm}

*图7-4 MCP在物联网平台中的架构示意。外部AI Agent只需连接一个MCP端点，后端资源由各服务层的OpenAPI自动聚合为工具目录；每个调用经基于OAuth的鉴权，并通过白名单与风险分级进行细粒度控制。*

MCP 的出现，使得物联网平台可以同时提供两种 AI 接入路径：Agentic Center（面向人）和 MCP（面向机器），两条路径共享同一套后端工具集。MCP 标准化了工具发现、鉴权和调用流程，让外部 Agent 的入驻从一次定制开发简化为配置连接。接下来的 7.2 节将展开第一条路径的实现细节——Agentic Center 如何基于 Spring AI 构建对话式运维。

## 7.2 Spring AI 与物联网集成

### 7.2.1 Spring AI 简介与配置

集成大模型到 Java 后端，一个常见的工程问题是：每个模型提供商都有自己的 SDK、协议和认证方式。如果 AIoT 平台要同时接入 GPT、Claude、DeepSeek 和通义千问，就得维护四套独立的 HTTP 客户端、错误处理和重试逻辑。Spring AI 恰好把这个胶水层抽了出来——它为 Java/Spring 生态提供了一套统一的 AI 模型调用抽象，切换模型提供商的成本被压缩到仅修改几行配置。

从设计定位看，Spring AI 更像一个适配器层，而不是独立的“Agent 框架”。核心接口 `ChatClient` 屏蔽了底层模型差异——它接收的是 OpenAI Chat Completions 风格的调用，输出的是标准化的 `ChatResponse`。对业务代码来说，无论后端连的是 OpenAI、Anthropic 还是 Ollama 本地模型，调用方式完全一致。除文本对话外，Spring AI 还提供了 `ImageClient`、`EmbeddingClient`、`AudioClient` 等接口。不过对物联网场景而言，`ChatClient` 与 Function Calling 的组合才是真正的核心能力——后者让模型能够按需调用 Java 方法获取实时数据或执行设备操作。Spring AI 将这种机制封装为 `@Tool` 注解和 `ToolCallback` 接口，开发者只需写一个普通方法，框架自动将其注册为可供模型调用的工具描述。

**为什么 IoT DC3 不接入一个独立的 AI 网关，而是选用 Spring AI？** 工程上有一个很直接的原因：DC3 是纯 Java 21 / Spring Boot 4 平台，每个服务都运行在 JVM 中。为引入 AI 再部署一套 Python 运行时，意味着要额外维护一个容器、一条语言桥接，以及两份运行时之间的网络通信可靠性。Spring AI 把 AI 能力拉近了现有 Java 进程：`ChatClient` 本身就是一个 Spring Bean，工具调用直接走 JVM 内的普通 Java 方法调用，认证上下文通过 Spring Security 过滤器链流转。模型拿到的设备数据和操作权限，不会超出操作员账号本身的 RBAC 范围。这种原生集成方式让工具方法可以直接引用业务 Service 层的代码，租户隔离在方法注解层面就能完成，不必额外维护一套权限等价映射。从运维视角看，这意味着少了一道需要部署、排障的中间环节，也少了一个跨语言调用的超时隐患。

配置入口很清晰。在现有 Spring Boot 项目中引入 Spring AI 只需要两步。第一步，在 `pom.xml` 中加入 Spring AI 的 BOM 和核心依赖：

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.ai</groupId>
            <artifactId>spring-ai-bom</artifactId>
            <version>1.0.0-M3</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency>
        <groupId>org.springframework.ai</groupId>
        <artifactId>spring-ai-openai-spring-boot-starter</artifactId>
    </dependency>
</dependencies>
```

第二步，在 `application.yml` 中配置模型提供商。Spring AI 默认使用 OpenAI Chat Completions 协议——这意味着只要后端暴露一个 OpenAI 兼容的端点，就能接入任何模型。下面展示了从云端模型切换到本地 Ollama 的配置方式：

```yaml
# 云端 GPT
spring:
  ai:
    openai:
      base-url: https://api.openai.com
      api-key: ${OPENAI_API_KEY}
      chat:
        options:
          model: gpt-4o

---
# 本地 Ollama（假设运行在 localhost:11434）
spring:
  ai:
    openai:
      base-url: http://localhost:11434/v1
      api-key: not-needed
      chat:
        options:
          model: deepseek-r1:7b
```

这两份配置共用同一套 `ChatClient` 代码。切换时只需激活对应的 Spring Profile，不需要改任何 Java 代码。DC3 的 Agentic Center 更进一步：支持在业务层面按会话指定不同的模型提供商，运维人员可以按成本、隐私或时延要求动态切换，而不必在环境级别硬编码。

配置中还可以自定义模型参数：`temperature` 控制输出的随机性，`max-tokens` 限制单次响应的最大长度，`stream` 开关决定是否启用流式输出。在物联网运维场景里，流式输出对交互体验很关键——当模型调用 `DeviceTool` 查询多个点位时，如果采用流式，操作员可以一边看模型“正在查询锅炉温度和风机转速”，一边等待完整结果，而不是面对空白界面猜测进度。下面是一个带参数的配置示例：

```yaml
spring:
  ai:
    openai:
      chat:
        options:
          temperature: 0.1      # 运维场景用低温度保证确定性
          max-tokens: 4096
          stream: true
```

配置完成后，开发者只需在代码中注入 `ChatClient` 即可使用。例如，在 Spring 组件中：

```java
@SpringBootTest
public class ChatClientExample {
    @Autowired
    private ChatClient chatClient;

    public void ask() {
        String response = chatClient.call("查询锅炉当前温度");
        System.out.println(response);
    }
}
```

实际使用时往往需要带上系统提示词和工具定义，Spring AI 提供了 `ChatClient.builder()` 模式来组装这些元数据。这些内容将在后续小节展开。

![图7-1 Spring AI 集成架构——从配置到响应的请求链路](../figures/chapter-07/fig-7-1.png){width=15cm}

*图7-1 Spring AI 集成架构。OpenAI API Adapter 是透明的代理层——它只做协议翻译，不引入额外逻辑。无论后端是云端 GPT 还是本地 Ollama，上层的 ChatClient 调用代码完全不变。*

总之，Spring AI 让 Java 工程师在 AIoT 集成中少踩许多跨语言、跨版本的坑，代价仅仅是多一个 Maven 依赖和几行配置。下一节将展示如何在物联网对话中真正利用这一能力——通过 Function Calling 让模型读取位号、控制设备。

### 7.2.2 ChatClient：统一对话接口

理解 `ChatClient` 的最佳方式，是从一段能跑起来的代码开始。假设你已经按照上一节的步骤配置好了依赖，现在打开一个 Spring Boot 测试类或者 `@Service`。

```java
@Autowired
private ChatClient chatClient;

public String askDeviceStatus() {
    String question = "请问 A 区三号锅炉的当前温度是多少？请给出数值和单位。";
    String answer = chatClient.prompt()
            .user(question)
            .call()
            .content();
    return answer;
}
```

这段代码展示了第一个核心设计：**调用方式**。`ChatClient` 把整个对话流程拆解成清晰的链式步骤：`prompt()` 构造消息 → `user()` 提供用户输入（也可加 `system()` 设定角色）→ `call()` 触发模型推理 → `.content()` 提取纯文本响应。链式风格在 Java 8 之后的生态里很常见，工程团队上手成本低。

**同步调用**（Sync Call）最简单也最容易调试。请求发出后，当前线程会阻塞在 `call()` 方法上，直到大模型返回完整结果。对物联网运维来说，一般在“查询一次状态”“解析一条指令”这类不需要实时流式展示的场景中使用。比如操作员说“帮我找一下上次报修的设备编号”，同步模式足够用，代码逻辑也直白。

但物联网很多场景需要实时反馈——读取锅炉温度时，如果模型要逐段生成分析报告，操作员不想等全部生成完才能看到第一行。这时需要 **流式调用**（Streaming Call），它也是 `ChatClient` 的内置能力：

```java
public void streamHealthReport() {
    Flux<String> reportStream = chatClient.prompt()
            .user("生成今天三号锅炉的健康报告，包含温度趋势和异常标记")
            .stream()
            .content();

    reportStream.subscribe(chunk -> {
        System.out.print(chunk);  // 或通过 WebSocket 推送
    });
}
```

`stream()` 返回一个 Reactor 的 `Flux<String>`，每次模型生成一个新 token（Token：大模型处理文本的最小单位，可理解为词语或子词片段），`subscribe` 回调就会触发一次。在实际的运维操作台里，用户看到的内容是一行行刷新出来的，不是等几分钟才刷出全文。这种体验对“告警诊断分析”这类长回复场景尤其重要。

**第三个维度是函数调用。** 7.2.3 节会专门展开，但这里先提一句：`ChatClient` 的 `.functions()` 方法能把 Spring Bean 注册为大模型可以自主调用的工具。当用户问“把三号锅炉的温度调到 85 度”时，大模型不是直接写代码，而是调用你注册的 `setTemperature` 函数，传入参数 `deviceId="boiler-03"`, `targetValue=85`，然后业务代码执行实际操作并返回结果。这个机制让 `ChatClient` 从“问答机器”变成了“操作入口”。

**典型对话场景。**

- **设备状态查询。** 用户：“查看厂区所有离线网关。” 模型调用 `DeviceTool.listOffline()`，返回结果后整理成自然语言：“共有 2 台离线：二号线 PLC（10:23 断电）、仓库温控器（09:15 网络断开）。”
- **日志分析。** 用户：“昨晚 2:00 到 3:00 之间三号锅炉的压力日志有没有异常？” 模型先调用 `PointValueTool.queryHistory()` 获取数据，再根据上下文中的正常压力范围判断趋势。最终输出：“发现 2:47 压力突升至 1.5 MPa（允许上限 1.2 MPa），持续约 4 分钟后回落。”
- **故障诊断。** 用户：“报警器一直在响，帮我看看怎么回事。” Agent 可先调用 `EventTool.listRecentAlarms()`，查询设备最近是否离线，如果离线则调用 `DeviceTool` 检查连接状态。最后给出诊断步骤：“可能原因：1）Modbus 连接断开；2）传感器模块供电异常。请确认机柜电源指示灯状态。”

每种场景的共性是：`ChatClient` 充当翻译层——把自然语言翻译成 API 调用，再把 API 返回的结果翻译回自然语言。不需要为每个设备写专门的解析逻辑。

**工程上的几点补充。** 同步调用虽然直观，但如果模型响应慢（几秒到几十秒），长时间阻塞会耗尽线程池。生产环境中通常将 `ChatClient` 放在异步执行器或 WebFlux 上下文中，或用 `async()` 方法配合 `CompletableFuture` 返回。流式调用则天然适合非阻塞架构，但也需要合理控制背压（Backpressure），避免推送太快导致前端缓冲区溢出。函数调用涉及用户确认和权限检查，一般会在工具执行前加一道拦截，例如 IoT DC3 的 Agentic Center 在 `ToolContext` 中传递租户和用户身份，业务代码根据 RBAC 判断是否允许写值。

**整体设计总结。** `ChatClient` 的三类调用对应物联网运维的不同需求：

| 调用模式 | 适用场景 | 数据流 | 典型例子 |
|---|---|---|---|
| 同步调用 (Sync) | 快速问答、简单指令 | 请求→阻塞→完整响应 | “查当前室温” |
| 流式调用 (Stream) | 长分析、实时看进展 | 请求→逐段推送 | “分析全天趋势异常” |
| 函数调用 (Function) | 执行操作、写值返回 | 请求→模型决策→调用业务代码→返回结果 | “把风机转速调到 1500 rpm” |

设计上，`ChatClient` 做了一层巧妙的抽象：它不关心你接的是 GPT-4o 还是 DeepSeek，只要模型暴露 OpenAI 兼容的 Chat Completions 端点，调用方式完全一致。这意味着物联网平台在“选模型”这件事上有了自由度——今天用 GPT，明天换成私有化部署的 DeepSeek，业务代码不需要改动一行，切换成本就是改配置文件。IoT DC3 的 Agentic Center 正是基于这个设计的产物，一条聊天消息变成设备指令，依赖的就是 `ChatClient` 的同步或流式对话接口与函数调用机制的组合。

掌握了这三种调用方式，接下来就可以看看函数调用具体是怎么定义和注册的——那就是 Spring AI 让大模型“碰”设备的关键机制。

### 7.2.3 Function Calling：让AI操作设备

ChatClient 能回答“锅炉温度是多少”，这很实用，但它仍然停留在“看”的层面。运维的真正需求是“动”——把风扇转速调到 1500 RPM、重启一台离线设备、切换阀门开度。**Function Calling**（也称工具调用，Tool Calling）就是让 LLM 从对话者变成操作者的关键机制。

#### 机制原理

Function Calling 的流程并不复杂。应用先向 LLM 注册一组可调用函数（名称、描述、参数结构），模型在推理时会判断用户意图是否匹配某个函数：匹配则输出一个结构化 JSON，包含函数名和参数，而不是直接输出自然语言。应用端拦截到这个 JSON 后，执行对应的后端方法，再把执行结果（通常是成功/失败、返回值）回填给模型，让模型据此生成最终的自然语言回复。整个过程没有魔法——LLM 不执行代码，它只负责“选函数、填参数”。

举个例子。用户问：“把A区3号锅炉的鼓风机转速调到 1500”，LLM 不会直接转动风机，它会输出类似 `{ "function": "setDevicePointValue", "arguments": { "deviceId": "boiler-003", "pointId": "fan-speed", "value": 1500 } }` 这样的结构。Spring AI 的 `ChatClient` 收到这个输出，匹配到对应的 `@Tool` 方法并调用，然后拿着执行结果生成一句“已成功将3号锅炉鼓风机转速设为 1500 RPM”。

这就是从“看”到“动”的分界。用一个假设场景来演示：控制一盏智能灯的开关。

#### 工具定义：开关灯

在 Spring AI 中定义一个可被 LLM 调用的工具极其简单——只需要在 Bean 方法上添加 `@Tool` 注解。下面是开关灯工具的实现。

```java
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;

@Component
public class LightTool {

    private boolean lightOn = false;
    private String currentLocation = "A区";

    @Tool(description = "开关指定区域的智能灯，返回灯的当前状态")
    public String toggleLight(
            @ToolParam(description = "区域名称，如A区、B区、C区") String location,
            @ToolParam(description = "目标状态：true为开灯，false为关灯") boolean turnOn) {
        
        // 在实际IoT DC3中，这里会调用DeviceTool的写入接口
        // 此处为示意逻辑
        this.lightOn = turnOn;
        this.currentLocation = location;
        
        String status = turnOn ? "已开启" : "已关闭";
        return String.format("%s的灯%s", location, status);
    }

    @Tool(description = "查询指定区域的灯当前是开还是关")
    public String getLightStatus(
            @ToolParam(description = "区域名称") String location) {
        
        String status = lightOn ? "亮着" : "关着";
        return String.format("%s的灯当前%s", location, status);
    }
}
```

两个关键点。第一，`@Tool` 注解的 `description` 是 LLM 理解该函数的唯一途径——描述越精确，模型越不容易误调用。第二，`@ToolParam` 的 `description` 帮助模型正确填充参数，例如 `turnOn` 参数如果用数字 1/0 而非布尔值，模型仍能通过描述推断出意图。

#### 工具注册与调用

工具定义好后，需要注册到 ChatClient 中。Spring AI 让这一步变得非常自然——只要将 `LightTool` 作为 Spring Bean 存在即可。`ChatClient.Builder` 会自动扫描并注册所有带有 `@Tool` 注解的方法。

```java
@Autowired
private LightTool lightTool;

public void demoFunctionCalling() {
    ChatClient chatClient = ChatClient.builder(chatModel)
            .build();  // 自动发现并注册所有@Tool Bean

    String userRequest = "帮我把A区的灯关了";
    String response = chatClient.prompt()
            .user(userRequest)
            .call()
            .content();

    // 输出：已关闭A区的灯
    System.out.println(response);
}
```

实际执行时，`ChatClient` 内部先向 LLM 发送用户消息加上工具描述（即 `LightTool` 的两个方法签名），模型判断“关灯”对应 `toggleLight(location="A区", turnOn=false)`，输出函数调用请求。客户端执行该函数，将结果返回给模型，模型最终合成回复。这一切对开发者透明。

如果用户连续提问，比如先问“A区灯什么状态”，再问“把它关了”，两次调用会穿过同一个对话上下文。这就是下一节“对话记忆”的作用——模型记得上一轮查出的状态。

#### 工程风险与控制

函数调用直接操控物理设备，容不得半点马虎。

**权限校验。** 不是所有用户都应该能操作所有设备。每个 `@Tool` 方法应通过 `ToolContext` 获取当前认证用户、租户 ID，然后在执行前做 RBAC 校验。IoT DC3 的做法是：AI 的所有动作最终都走平台真实 API，经网关注入主体上下文，再由鉴权中心做权限校验与租户隔离——模型拿不到比对应账号更多的权限（资料：[S9]）。

**参数验证与范围约束。** LLM 填充的参数可能超出预期范围，比如把转速设为 100000。工具方法内部必须进行参数合法性校验，必要时增加 `@ToolParam` 的 `min` / `max` 属性（如果模型支持）。对于高风险写操作，可设计“参数预览+确认”环节，让用户在界面上确认后再执行。

**回滚与幂等性。** 设备操作未必总能成功：网络中断、设备离线、协议超时。工具方法应返回清晰的状态码和错误信息，让模型能据此生成用户可理解的提示。对于非幂等操作，必须保证工具方法本身幂等，避免重试时产生不一致状态。

**避免“误操作”的自然语言陷阱。** 用户说“把所有设备都关掉”可能是个玩笑，模型却可能真的发起批量操作。工程实践中，对批量、高危操作应增加一道硬约束——要么要求用户二次确认（高风险确认模式），要么在工具描述中加入警告语句引导模型在批量操作前反问。

![图7-4 Function Calling 交互流程：从自然语言到设备操作](../figures/chapter-07/fig-7-4-function-calling-flow.png){width=15cm}

*图7-4 展示了 Spring AI Function Calling 的完整调用链路，以“关A区灯”为例。操作员的自然语言请求首先到达 ChatClient，ChatClient 将消息连同 LightTool 的工具描述发送给 LLM。LLM 推理后返回 JSON 格式的函数调用请求，ChatClient 解析并调用对应的 @Tool 方法，将执行结果回填给 LLM 后，LLM 生成最终的自然语言回复返回给操作员。*

知道了如何定义工具，下一步自然要问：多轮对话中，模型如何记得上一轮查出的设备 ID 和参数？这就要引入对话记忆机制。

### 7.2.4 对话记忆：保持上下文连续

对话式运维中，操作员可能先查询历史数据，接着要求对某个异常段执行操作。如果没有记忆机制，模型无法解析第二句话中的指代对象——上一轮提到的“异常段”与第二轮要调整的参数之间没有显式关联。这不是可用性问题，而是无状态 API 与多轮交互之间的结构性矛盾：大语言模型每次请求默认独立处理，上一轮的信息不会自动带入下一轮，应用层必须主动管理会话历史。

#### 无状态设计的工程代价

Chat Completion API 遵循无状态设计，每次请求携带独立的完整消息，模型内部不做跨请求关联。这简化了 API 本身的实现，但将上下文管理的责任完全交给了调用方。在物联网运维中，一个会话可能持续多轮，涉及设备查询、参数解读、命令下发、结果确认。如果每轮都从零开始，指代解析必然失败，“多轮对话”就会退化成单轮问答。这是选择 ChatClient 时必须考虑的第一层代价：你获得了无状态服务的高可用伸缩，就必须用额外内存或存储换回上下文连续性。

#### Spring AI 的三种记忆策略

Spring AI 通过 `ChatMemory` 接口和 `MessageChatMemoryAdvisor` 顾问提供了对话记忆的标准化接入。三种内置策略在物联网场景中的适用性有明显区别：

| 策略 | 原理 | 运维场景适用性 |
|---|---|---|
| 消息历史 | 将完整消息列表（用户+助手）直接附加到每次请求 | 短轮次对话（通常10轮以内），保留上下文且无信息损失 |
| 摘要记忆 | 将历史压缩为一段摘要，避免token溢出 | 长轮次对话或token预算紧张时使用，但需要保留关键操作结果 |
| 知识图谱记忆 | 维护实体关系，仅检索相关实体获得上下文 | 复杂推理场景，如追溯多台设备的历史操作链 |

运维对话通常围绕有限设备和位号展开，轮数可控，消息历史模式最直接。但当对话拉长或涉及频繁的 Tool Calling 反馈时，摘要记忆做自动压缩是更稳妥的选择。压缩规则需要特别注意：操作类历史必须保留执行结果与状态码，避免模型因上下文丢失而重复执行相同的下发指令。

#### 关键实现：MessageChatMemoryAdvisor 与 conversationId

`MessageChatMemoryAdvisor` 通过装饰器模式将历史管理透明化。每次 `chatClient.call()` 之前，Advisor 自动从 `ChatMemory` 中取出与当前 `conversationId` 关联的历史消息注入到提示词中，调用结束后再将本次消息写入。`conversationId` 是会话唯一标识，不同会话使用不同 ID 即可隔离上下文。以下示意代码展示典型实现：

```java
ChatMemory chatMemory = new InMemoryChatMemory();
var advisor = new MessageChatMemoryAdvisor(chatMemory);

// 第一轮
String query1 = "昨天三号线平均温度是多少？";
String response1 = chatClient.prompt(query1)
    .advisors(advisor)
    .param(ChatMemoryAdvisor.CHAT_MEMORY_CONVERSATION_ID_KEY, "session-line-3")
    .call().content();

// 第二轮，相同 conversationId 即可关联前文
String query2 = "对这个温度区间，风冷参数该怎么调？";
String response2 = chatClient.prompt(query2)
    .advisors(advisor)
    .param(ChatMemoryAdvisor.CHAT_MEMORY_CONVERSATION_ID_KEY, "session-line-3")
    .call().content();
```

`InMemoryChatMemory` 适用于开发与测试，生产环境建议对接 Redis 等外部存储，以便跨进程共享会话状态，同时提供持久化与故障恢复能力。

#### 对话长度与 token 预算的工程权衡

全量历史注入存在明显的 token 成本问题。对于上下文较短的模型，保留多轮完整对话会很快用尽预算，留给指令与工具返回的空间所剩无几。Spring AI 的 `chat-memory-advise-response-size` 配置可以限制注入的历史消息条数，超出部分可通过摘要器压缩为一段话附加在系统提示中。工程实践中，常见的折中是保留最近若干轮全量历史，更早的历史由摘要器生成一段结构化摘要，摘要中必须包含关键操作结果与时间戳，避免模型因信息缺失而重复执行或误判。

#### IoT DC3 中的会话持久化

IoT DC3 的 Agentic Center 将 `ChatMemory` 对接平台内部表结构，对话记录直接写入中心表，支持会话回放、审计与故障复盘。操作员一句“看看上次对三号线做了什么”，模型即可检索对应会话的完整历史。这种可追溯能力不仅为多轮交互提供上下文连续性，更将每一次运维操作数字化为可审计的记录，是运维合规与事故回溯的基础设施。

对话记忆是 Function Calling 在多轮场景中准确执行的先决条件——模型必须知道上一轮的操作结果，才能判断下一轮应查哪个位号、调哪个参数。没有它，Tool Calling 只能在单轮中生效，应用价值自然大打折扣。

## 7.3 IoT DC3 的 Agentic Center 实践

### 7.3.1 IoT DC3 Agentic Center 架构概述

操作员发现产线温度异常，需要在一个界面查位号值，切到设备管理找风机执行器，再回到命令界面下发转速调整。数据在、接口在，但操作路径割裂是物联网运维常见的工程瓶颈。Agentic Center 要打破的正是这层界面锁死——让大语言模型在平台上能读能写，把一个跨界面的操作链压缩成一句自然语言。

#### IoT DC3 平台简况

IoT DC3 是一个开源物联网基础平台，核心服务以微服务形式运行。在进入 Agentic Center 之前，DC3 已经具备四层参考架构的完整能力：设备接入、设备管理、数据汇聚、基础运维工具。这些能力封装在几大中心服务中——`dc3-center-manager` 处理设备元数据，`dc3-center-data` 负责位号值的读写与存储，`dc3-center-auth` 管理租户身份和 RBAC 权限校验（资料：[S7]）。DC3 对数据的抽象是“位号”——一个附带了语义的物理量描述，例如`锅炉_温度`。这种抽象使得平台向上提供的是标准化位号值接口，而非原始传感器报文或寄存器地址。

#### Agentic Center 的设计目标

Agentic Center 不是新建独立的 AI 子系统，而是把大语言模型嵌入 DC3 现有的运维流程，让 AI 既能读取平台数据，也能操作平台设备（资料：[S6]）。设计上遵循两条硬性原则：

1. **所有 AI 操作最终走平台真实 API**。模型不直接访问数据库，不绕过鉴权中心。每次工具调用都经过网关注入用户主体上下文，走 RBAC 权限校验——AI 拿到的权限不超过操作员账号自身的权限。这条原则保障了 AI 不会成为权限后门。
2. **工具就是平台服务层的映射**。Agentic Center 内置的 `@Tool` 工具类，每个都是对已有服务层方法的薄包装，不重复业务逻辑（资料：[S6]）。已有的设备管理、数据读写、驱动启停功能，只需在方法上标注 `@Tool` 注解，就能暴露给大模型。工具集的维护成本几乎为零——平台每增加一个 API，对应的工具可以同步跟上。

架构选择 Spring AI 的原因有两个。一是原生 JVM 集成：DC3 是纯 Java 21 平台，引入 Spring AI 无需额外 Python 运行时、不必管理两个语言运行时之间的网络桥接。`ChatClient` 是一个 Spring Bean，工具调用是普通 Java 方法调用，认证上下文走已有的 Spring Security 过滤器链。二是协议兼容性：Spring AI 的 `ChatClient` 默认采用 OpenAI Chat Completions 协议，可以接入任何提供 OpenAI 兼容端点的模型——GPT、Claude、DeepSeek、通义千问，甚至本地运行的 Ollama 实例（资料：[S6]）。

#### 架构层次：从设备到对话的四层结构

从部署和职责视角，Agentic Center 的架构可以拆成四层：

- **用户交互层**：操作人员看到的入口，可以是 DC3 Web 界面中嵌入的聊天窗口，也可以通过 `POST /api/v3/agentic/v1/chat/completions` 接入的任意客户端。消息格式兼容 OpenAI Chat Completions 规范，支持流式响应和非流式请求。
- **AI Agent 层**：核心是 `dc3-center-agentic` 服务，包含一个 Spring AI 的 `ChatClient` Bean，加载了多个 `@Tool` 工具方法。会话管理（`MessageChatMemoryAdvisor`）和模型路由配置也位于这一层。AI Agent 层只做意图识别与工具调度，业务请求通过 Feign 客户端转发给下一层。
- **平台服务层**：包括管理、数据、鉴权等中心服务。Agentic Center 通过 Feign 客户端调用这些服务，方式与普通前端请求完全一致——不走旁路，不设特殊通道。
- **数据与设备层**：底层包括 PostgreSQL（关系数据）、MongoDB（位号历史值时序存储）、以及通过驱动网关连接的物理设备。设备本身对 AI 不可见，AI 看到的是经过归一化的位号值。

![图7-6 Agentic Center 四层架构示意图](../figures/chapter-07/fig-7-6.png){width=15cm}

*图7-6 Agentic Center 四层架构示意图。从上至下依次为用户交互层、AI Agent层、平台服务层、数据设备层，展示了各层组件及层间通信方式。*

#### 工具即是能力：内置工具集

Agentic Center 出厂自带的多个 `@Tool` 工具类，覆盖平台最主要的领域对象。其中 `DeviceTool` 用于查询设备状态与详情，`DriverTool` 管理驱动启停，`PointValueTool` 读取和写入位号值——这三个工具直接支撑了“对话驱动设备操作”的核心链路（资料：[S6]）。每个工具方法上的 `@Tool` 注解包含 `description` 属性，描述工具的能力和参数，这些描述被注入模型上下文，帮助模型判断何时调用哪个工具。

#### 架构之外的权衡

Agentic Center 有一个重要的“不为”选择：不做模型推理。Agentic Center 只负责意图识别和工具调度，真正的模型推理发生在远端或本地部署的模型服务中。这意味着 Agentic Center 不部署大模型，不管理 GPU 资源。模型推理和平台逻辑解耦后，你可以把 GPT-4o、DeepSeek 或一个跑在 Ollama 上的 7B 模型接到同一个 Agentic Center，无需修改代码（资料：[S6]）。

下一节，我们从工具集中选取三个关键工具——`DeviceTool`、`DriverTool`、`PointValueTool`——拆解具体实现，并演示一次完整的“对话驱动设备操作”。

#### 7.3.2 DeviceTool：设备检索与控制

设备是物联网平台的核心实体。在传统运维界面中，操作员需要登录 `dc3-center-manager` 的控制台，通过菜单跳转到设备列表页，再输入设备名称或编码进行搜索。如果要查看某个设备的详细信息，还需要双击进入详情页；要修改设备参数，则要在多个表单字段间切换。这种操作路径对于单个设备尚可接受，但当运维人员需要批量处理数十台设备、或者在处理告警时临时查询设备元数据，界面切换的成本就会迅速累积。

Agentic Center 中的 DeviceTool 解决的就是这个问题：让大语言模型（LLM）直接通过自然语言触发设备检索与控制操作，把多步界面操作压缩为一句自然语言指令。

DeviceTool 是 Agentic Center 内建的 10 个 `@Tool` 工具类之一，封装了 DC3 设备管理服务（`dc3-center-manager`）的核心 API（资料：[S9]）。它覆盖三种常见操作类型：设备列表检索、设备详情查询、设备属性写入。每种操作对应一个或多个 `@Tool` 方法，这些方法在 Spring AI 框架下被注册为模型可调用的工具函数。

**从用户聊天消息到设备操作的路径**

当一位运维人员对 Agentic Center 说“查询三楼温控器最近的状态”时，背后发生的过程涉及多个组件协作。下面的架构图清晰展示了从自然语言到设备操作的完整数据流。

![DeviceTool 调用链路](../figures/chapter-07/fig7-3-2-1.png){width=15cm}

*|*

**DeviceTool 的 Java 实现**

在代码层面，DeviceTool 是 Spring Bean，方法上标注 `@Tool` 注解，Spring AI 在启动时自动扫描并注册这些工具到模型可用的函数列表中。每个工具方法都会包装 `dc3-center-manager` 已有服务层的方法，不存在重复的业务逻辑（资料：[S11]）。

下面展示一个简化的 DeviceTool 实现，包含“列出设备”和“写入设备属性”两个核心方法：

```java
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;
import com.dc3.center.manager.service.DeviceService;
import com.dc3.center.data.service.PointValueService;

@Component
public class DeviceTool {

    private final DeviceService deviceService;
    private final PointValueService pointValueService;

    public DeviceTool(DeviceService deviceService, PointValueService pointValueService) {
        this.deviceService = deviceService;
        this.pointValueService = pointValueService;
    }

    /**
     * 根据位置或名称关键词列出匹配的设备列表。
     * LLM 在需要列举某个区域或类型的设备时会调用此方法。
     */
    @Tool(description = "根据位置或名称关键词列出设备列表，支持模糊匹配")
    public String listDevices(
            @ToolParam(description = "查询关键词，例如'三楼温控器'或'锅炉'，支持设备名称和位置的模糊检索") String keyword,
            ToolContext toolContext) {
        var tenantId = toolContext.getContext().get("tenantId");
        // 实际调用 deviceService 执行模糊查询，返回 JSON 格式的设备摘要
        var devices = deviceService.searchByKeyword(tenantId, keyword);
        return devices.stream()
                .limit(10)  // 限制返回数量，避免超出模型上下文窗口
                .map(d -> String.format("设备名：%s，类型：%s，位置：%s，状态：%s",
                        d.getName(), d.getDeviceType(), d.getLocation(), d.getStatus()))
                .collect(Collectors.joining("\n"));
    }

    /**
     * 写入指定设备的某个点位值。
     * 例如写入调节参数、开关指令等。此操作属于高风险，需做二次确认。
     */
    @Tool(description = "写入指定设备的属性点值，例如设置温度调节目标值或开关状态")
    public String writePointValue(
            @ToolParam(description = "设备ID（数字）") Long deviceId,
            @ToolParam(description = "点位（属性）编码，例如 temperature_setpoint") String pointCode,
            @ToolParam(description = "要写入的值，字符串格式，实际类型根据点位定义自动转换") String value,
            ToolContext toolContext) {
        // 权限校验：只有拥有 write 权限的租户可执行
        var tenantId = toolContext.getContext().get("tenantId");
        // 高风险确认：写入操作会弹出确认对话框，必须人工点击确认才能执行
        // 返回值给 LLM，LLM 再生成确认询问
        return "准备写入：设备 " + deviceId + " 的 " + pointCode + " 设为 " + value + "。请确认是否执行？";
    }
}
```

代码中的 `ToolContext` 参数由 Spring AI 自动注入，携带当前会话的租户身份和认证上下文。这样，DeviceTool 方法执行时不需要关心用户是谁、是否有权限——这些已经在网关层和鉴权中心处理完毕，工具方法可以直接信任传入的上下文（资料：[S5]）。

**两个典型的运维场景**

**场景一：设备检索。** 某新能源公司的运维值班员在 Agentic Center 对话界面输入：“查一下屋顶光伏板阵列的在线状态”。LLM 收到文本后，判断需要调用 DeviceTool 的 `listDevices` 方法，参数 keyword 为“屋顶光伏”。DeviceTool 接收到查询请求，调用 `deviceService` 执行模糊匹配，返回“设备名：屋顶光伏-南区，类型：光伏逆变器，位置：3号厂房楼顶，状态：在线”以及“设备名：屋顶光伏-北区，类型：光伏逆变器，位置：3号厂房楼顶，状态：离线”两条记录。LLM 组织自然语言回答：“截至目前，屋顶光伏区域有 2 台逆变器，其中北区离线，南区在线。”——整个过程约两秒，操作员不用打开任何设备管理页面。

**场景二：批量写入操作。** 运维人员发现北区光伏逆变器离线，定位原因是功率限值参数需要调整，于是输入：“将北区光伏的出力上限调到 50 kW”。LLM 调用 `writePointValue`，设备 ID 指定为北区逆变器，pointCode 为 `power_limit`，值为 `50`。工具方法返回“准备写入：设备 1024 的 power_limit 设为 50。请确认是否执行？”。LLM 将确认询问呈现给用户，用户在界面上点击“确认”后，Agentic Center 再次调用工具方法执行实际写入，并将结果反馈给 LLM，最终返回操作成功的自然语言消息。

**工程权衡**

DeviceTool 的设计有几个值得注意的权衡点。第一，工具方法的返回结果必须是结构化的文本，而非二进制数据或分页列表。因为 LLM 的上下文窗口有限，DeviceTool 在 `listDevices` 中做了 `limit(10)` 的限制，将查询结果截断为最多 10 条，超出的部分让模型提示用户“是否查看更多”（资料：[S10]）。第二，写入类的操作使用了两阶段提交模式——先让工具方法返回一个“确认询问”，用户确认后再执行实际写入。这避免了模型因幻觉或误触而错误下发指令。第三，所有 DeviceTool 方法内部不包含任何业务逻辑，仅做代理转发，这样不影响原有服务层的单元测试覆盖率，也降低了 Agentic Center 的维护负担。

### 7.3.3 DriverTool：驱动配置与管理

驱动是物联网平台连接物理世界的桥梁。在 IoT DC3 的四层架构中，驱动层负责协议适配和数据归一化：Modbus RTU 报文、OPC UA 变量订阅、MQTT 主题——全在驱动实例中完成到带语义的位号值流的转换（资料：[S2]）。传统运维中，添加一个新驱动实例意味着操作员需要登录管理界面、选择驱动类型、填写通信参数、测试连通性，最后再手动启动。一旦配置参数错误，比如 IP 写错或端口不通，整个设备组的采集都可能中断。DriverTool 的目标就是让 LLM 通过自然语言直接完成驱动实例的创建、启停与状态查看，把这几步操作压缩成一句对话。

**核心能力**

DriverTool 是 Agentic Center 内建的 10 个 `@Tool` 之一，封装了 `dc3-center-manager` 中的驱动管理接口（资料：[S9]）。它覆盖三类操作：驱动类型列表查询、驱动实例创建与配置、驱动实例状态查看与启停。由于写操作可能中断现有数据采集，所有写操作均标记为 `@WriteOperation(requiresConfirmation = true)`，用户必须二次确认才能执行（资料：[S3]）。下面是 DriverTool 的核心代码骨架，省去了异常处理和日志记录。

```java
@Component
public class DriverTool {

    private final DriverClient driverClient;

    public DriverTool(DriverClient driverClient) {
        this.driverClient = driverClient;
    }

    @Tool(description = "列出所有可用的驱动类型及其简要描述")
    public List<DriverTypeBO> listDriverTypes(ToolContext toolContext) {
        var tenantId = AgenticToolContextUtil.extractTenantId(toolContext);
        return driverClient.listDriverTypes(tenantId);
    }

    @Tool(description = "为指定设备创建或更新驱动实例，需要用户确认")
    @WriteOperation(requiresConfirmation = true)
    public DriverInstanceBO configureDriver(
            @ToolParam(description = "设备ID") Long deviceId,
            @ToolParam(description = "驱动类型编码，例如 MODBUS_TCP") String driverTypeCode,
            @ToolParam(description = "驱动配置参数，JSON格式，如 {\"ip\":\"...\", \"port\":502}") String configJson,
            ToolContext toolContext) {
        var tenantId = AgenticToolContextUtil.extractTenantId(toolContext);
        return driverClient.configureDriver(deviceId, driverTypeCode, configJson, tenantId);
    }

    @Tool(description = "启动或停止指定设备关联的驱动实例")
    @WriteOperation(requiresConfirmation = true)
    public boolean toggleDriver(
            @ToolParam(description = "设备ID") Long deviceId,
            @ToolParam(description = "操作：start 或 stop") String action,
            ToolContext toolContext) {
        var tenantId = AgenticToolContextUtil.extractTenantId(toolContext);
        return driverClient.toggleDriverInstance(deviceId, action, tenantId);
    }
}
```

`listDriverTypes` 是只读操作，无需确认。`configureDriver` 和 `toggleDriver` 是写操作，标有 `@WriteOperation(requiresConfirmation = true)`。每次调用时，Spring AI 框架会自动拦截这个注解，在返回给用户的响应中嵌入一条确认提示——“确认要为设备 1024 配置 Modbus TCP 驱动？”，用户在收到提示并输入“确认”或“是”之后，工具调用才会真正执行。

**调用流程与风险控制**

当操作员说“为新装的温度传感器启用 Modbus 驱动”，Agentic Center 的处理路径如下：

1.  LLM 解析意图为“配置驱动”，匹配到 `listDriverTypes` 和 `configureDriver` 工具。
2.  先调用 `listDriverTypes`，确认平台支持 Modbus TCP 和 Modbus RTU 两种变体。
3.  通过 DeviceTool（参见 7.3.2 节）的 `searchDevices` 获取传感器的设备 ID。
4.  调用 `configureDriver` 传入通信参数（IP、Port、SlaveId）。
5.  由于 `configureDriver` 是高风险写操作，系统返回确认请求：“是否为传感器（ID:1024）启用 Modbus TCP 驱动，连接到 192.168.1.100:502？”
6.  用户确认后，执行 INSERT 到数据库记录。
7.  LLM 再调用 `toggleDriver` 启动驱动实例。

下面的时序图展示了完整调用路径，重点突出了写操作所需的用户确认分支。

![图7-6 DriverTool驱动配置时序图](../figures/chapter-07/fig-7-6-2.png){width=15cm}

*图7-6 展示 DriverTool 处理用户‘启用Modbus驱动’指令时的完整交互流程，写操作经用户确认后才提交到数据库，防止误中断采集。*

驱动配置的写操作风险高——错误参数可能中断采集甚至损坏设备。Agentic Center 施加三重保护。第一重是代码注解级的确认拦截，用户不“点头”就不执行。第二重是 RBAC 权限校验，所有工具调用都会带上从 Spring Security 过滤器链提取的租户和用户上下文，模型获得的权限不会超过当前登录用户（资料：[S9]）。第三重是审计日志，每次对驱动实例的创建、修改、启停都会写入日志表，可追溯“谁在何时通过哪句话改变了驱动配置”。另外，工程上还有一个实用限制：为了防止 LLM 每轮对话都全量查询驱动状态（导致上下文溢出），Agentic Center 只返回用户提及的那台设备的驱动状态，其余驱动实例按需通过子查询提供。

**工作流示例**

考虑下面这段典型的运维对话，展示了 DriverTool 在真实场景下的交互流程。

> **操作员**：“三车间新装的温湿度传感器，启用 Modbus 驱动。”
>
> **Agentic Center**（先调 `listDriverTypes` 发现平台支持两种 Modbus 变体）：“支持 Modbus TCP 和 Modbus RTU。请问用哪种？”
>
> **操作员**：“Modbus TCP，IP 192.168.100.50，端口 502，从站 1。”
>
> **Agentic Center**（通过 DeviceTool 查询到该车间有 12 个温湿度传感器）：“匹配到 12 个传感器，将为它们配置 Modbus TCP 驱动（192.168.100.50:502）。确认实施？”
>
> **操作员**：“确认。”
>
> **Agentic Center**（逐个创建驱动实例并启动，最后汇总结果）：“11 个传感器成功启用驱动，1 个（设备编码 S3012）连接超时。是否需要检查该传感器的网络参数？”

这个示例中，Agentic Center 不仅执行了模型自动选择的配置批处理，还利用 LLM 识别到了 1 台设备的连接失败，并以自然语言反馈给操作员。传统管理界面在这里只能展示一个“成功数/失败数”的静态列表，而 LLM 能够主动建议下一步排查方向。这就是 DriverTool 对比传统运维界面的关键差异。

### 7.3.4 PointValueTool：实时数据读写

点位（Point）是物联网平台中数据的最小语义单元。一台温控设备可以有“当前温度”“目标温度”“风机转速”“开关状态”等多个点位，每个点位独立对应一个数据源和类型。运维人员最频繁的操作就是查点位值和改点位值。传统做法需要登录管理界面、找到设备树、展开点位列表、再选操作。PointValueTool 把这几步压缩成一次对话：用户说“看一下3号锅炉的出口温度”，LLM 就能调用 PointValueTool 读到最新数值并返回。

Agentic Center 内建的 `PointValueTool` 是 10 个 `@Tool` 之一（资料：[S9]），它封装了 `dc3-center-data` 服务提供的实时数据读写接口，与 `DeviceTool`（查设备元数据）、`DriverTool`（管驱动实例）形成互补。读操作没有副作用，写操作则会把指令下发到驱动层进而影响物理设备。因此写入操作必须附加参数校验（值范围、数据类型）和权限限制（仅允许配置了写权限的用户），并在高风险动作前要求人工确认，写入操作被标记为 `@WriteOperation(requiresConfirmation = true)`（资料：[S3]）。每次写入都会写入操作日志，与 `EventTool` 联动生成一条事件记录，供后续审计和告警联动（资料：[S9]）。

#### 读取实现：无副作用的快速查询

读取实时点位值是 PointValueTool 最基本的功能。核心方法 `getLatestPointValue` 通过点位 ID 从时序数据库中取出最新值——这个过程不涉及写操作，LLM 可以在多轮对话中反复调用。下面是基于 Spring AI 的 `@Tool` 注解实现：

```java
@Component
public class PointValueTool {

    private final PointValueService pointValueService;

    @Tool(description = "获取指定测点的最新实时值，返回包含数值、时间戳和单位")
    public PointValueBO getLatestPointValue(
            @ToolParam(description = "测点ID，可在设备详情页或PointTool中查到") Long pointId,
            ToolContext toolContext) {

        String tenantId = AgenticToolContextUtil.getTenantId(toolContext);
        // 调用服务层，返回包含value、time、unit的BO对象
        return pointValueService.getCurrentValue(tenantId, pointId);
    }
}
```

整条路径没有多余的开销：LLM 收到用户的“查看当前温度”指令后，先通过 `DeviceTool` 定位设备，再通过 `PointTool` 确定点位 ID，最后调用 `getLatestPointValue` 拿到数值，组织成自然语言回复。

#### 写入实现：带确认与校验的值写入

写入操作必须谨慎。`PointValueTool` 中的写入方法 `writePointValue` 除了参数校验，还会在返回结果中标记 `requiresConfirmation = true`，让前端弹窗等待用户确认后才真正执行（资料：[S3]）。下面的代码展示了完整的校验流程：

```java
@Tool(description = "写入指定测点的值，需要用户二次确认")
@WriteOperation(requiresConfirmation = true)
public WriteResult writePointValue(
        @ToolParam(description = "测点ID") Long pointId,
        @ToolParam(description = "要写入的值，注意单位（如温度用摄氏度、角度用度）") String value,
        ToolContext toolContext) {

    String tenantId = AgenticToolContextUtil.getTenantId(toolContext);
    String operator = AgenticToolContextUtil.getUserId(toolContext);

    // 1. 参数校验
    PointBO point = pointValueService.getPointMeta(tenantId, pointId);
    if (point == null) {
        return new WriteResult(false, "点位不存在");
    }
    if (!validateValueFormat(point.getType(), value)) {
        return new WriteResult(false, "值格式错误，预期类型：" + point.getType());
    }
    if (!validateValueRange(point.getMin(), point.getMax(), value)) {
        return new WriteResult(false, "值超出范围，允许范围：" + point.getMin() + " ~ " + point.getMax());
    }

    // 2. 权限检查
    if (!authService.hasPointWritePermission(operator, pointId)) {
        return new WriteResult(false, "无写入权限");
    }

    // 3. 执行写入
    boolean success = pointValueService.write(tenantId, pointId, value);
    return new WriteResult(success, success ? "写入成功" : "写入失败，请检查设备连接");
}
```

写入操作的回执与实际下发之间有一个确认环节：LLM 先返回一个拟操作摘要，用户确认后平台再调用相同的 `writePointValue`。此时跳过初次验证，直接执行第3步。这种设计防止了 LLM 因幻觉或错误推理而直接遥控物理设备。

#### 写入操作的额外风险控制

除了代码层面的校验，IoT DC3 还引入了风险分级和速率限制。系统根据点位的元数据（如“是否属于安全关键设备”）自动判断操作风险级别，高级别操作需要额外的审批流。同时，单用户每分钟的写入调用次数被限制在合理范围内，防止意外高频操作压垮驱动层。这些策略与 `@WriteOperation(requiresConfirmation = true)` 一起构成了对物理世界操作的三重防护：参数校验、人工确认、风险分级。

在 IoT DC3 的实际部署中，PointValueTool 的高频场景包括“查看所有超限温度点”“把1号反应釜搅拌速度调到200rpm”。写入操作会自动记录完整上下文（操作人、时间、旧值、新值），供后续审计。与 `EventTool` 配合还可以在写入后自动生成一条事件记录用于告警联动。PointValueTool 让 LLM 从“旁观者”变成了“执行者”，但写入门槛的谨慎设计，保证了物理世界不会因为一句错误的对话而失控。

![PointValueTool 读写调用流程](../figures/chapter-07/figure-7-4.png){width=15cm}

*图7-4 PointValueTool 读写调用流程*

### 7.3.5 自然语言运维：对话替代仪表盘

运维人员每天要在多个功能页面间来回切换：设备列表、点位查询、实时曲线、告警列表、日志检索、驱动状态。完成一次复合查询（比如“查所有温度超限的设备”），传统做法是先打开设备管理页面筛选车间，再进入实时数据页面逐台查温度值，最后人工比较上限——全程依赖熟练度和注意力。Agentic Center 把这一整套交互压缩成一个对话输入框：用户说一句话，模型自己去判断该调哪个工具、按什么顺序调。

#### 一次对话，四个工具

以下对话基于 IoT DC3 Agentic Center 的典型交互模式，属于假设场景下的示意案例，非真实系统日志。

```
用户：帮我检查一下3号车间所有设备的状态，尤其是温度有没有超过上限的。

Agentic Center：正在查询3号车间的设备列表……找到多台设备。
接下来检查各设备当前温度点位的实时值……

结果汇总：
1. PLC-01（温控器）——温度偏高，超过上限
2. PLC-02（变频器）——温度正常
3. PLC-03（风机）——温度正常
4. PLC-04（液压站）——温度偏高，超过上限

超限设备共2台：PLC-01和PLC-04。
建议：PLC-01当前温度超过上限较多，请检查散热风扇或降低负载；
PLC-04温度超限，建议检查液压油冷却系统。
是否需要我为其中任何一台执行降温操作？

用户：把PLC-01的散热风扇转速调到高速档。

Agentic Center：好的，正在查询PLC-01的设备信息、散热风扇对应的点位ID及有效取值范围……
确认信息如下：
- 设备：PLC-01
- 目标点位：FAN_SPEED（散热风扇转速）
- 目标值：高速档（取值范围由设备配置定义）
此操作会触发实际设备指令，是否确认执行？（输入y确认）

用户：y

Agentic Center：指令已下发，执行成功。
当前散热风扇转速已设为高速档，建议稍后再次查询PLC-01的温度变化。
```

这一轮对话，Agent 依次调用了四个工具：`DeviceTool`（查3号车间设备列表）、`PointValueTool`（查每台设备温度点位的实时值）、`CommandTool`（下发写点指令给PLC-01的风扇转速点位）——外加一次高风险确认环节。用户敲了三次键盘，完成了传统界面需要多次页面跳转才能做完的事。

#### 多工具编排：Agent 如何“拆任务”

用户说“查看温度超限的设备”，这句话模型不会直接返回硬编码结果。Agentic Center 内部的 Agent 循环（ReAct 模式，即 Reason + Act，先推理再行动）把它拆成一个任务链（示意逻辑）：

1. **语义解析**：识别出“设备”“温度”“超限”三个关键实体，明确任务是“查询所有设备 → 获取温度的实时值 → 与温度上限做比较 → 返回超限的设备”。
2. **工具调用**：先调用 `DeviceTool` 获取3号车间所有设备的列表；对每台设备调用 `PointValueTool` 读取其当前温度和温控上限值。
3. **计算与判断**：将读到的实时值与上限值做比较，找出超限项。
4. **自然语言生成**：将结果组织成可读的格式，并在发现超限设备后给出建议。
5. **待命**：用户后续的操作指令（如调转速）触发新一轮工具调用。

这个“拆任务”能力来自 Tool-Calling 和 Agent 的规划机制——不需要人工预先编写每一步的逻辑。对比传统运维：运维人员得先打开设备管理模块，筛选出3号车间的设备列表，记住每台的温度点位ID，然后进入实时数据页面逐台查询，再手算哪些超限——全程依赖熟练度和注意力。

#### 对话替代仪表盘：适用边界

不是所有运维操作都适合对话式。从 Agentic Center 的实践中可以总结三个适用准则：

- **查询类优先**：查状态、查趋势、查元数据——信息密度低、操作频次高，对话替代收益最大。
- **跨对象关联操作**：“所有温度超限的设备”“CPU利用率最高的三台服务器”这类需多步查询和聚合的任务，比逐页翻找高效得多。
- **带有解释的操作**：不仅告诉结果，还解释原因和建议——传统界面通常只给数字，不给上下文。

不适合对话的则包括：批量配置设备（成百上千台设备的参数统一写入）、高频实时监控（毫秒级刷新）、算法调试（模型看不到内部系数）。这些场景仍需要专业的仪表盘和自动化脚本。

#### 对话式运维背后的工程权衡

在享受简洁的同时，有两个问题必须回答。

**第一，多轮对话中的上下文如何保持。** 用户问完“温度超限的设备”又接着问“它们在过去一小时内的变化曲线”，Agent 需要知道“它们”指的是刚才那两台超限设备。Spring AI 的 `MessageChatMemoryAdvisor` 负责维护对话历史，把之前查询的结果摘要注入当前轮次的系统提示中。Agentic Center 另外把每次工具调用的结果摘要持久化到会话表，重启后也能恢复上下文。

**第二，用户信任如何建立。** 一次误操作可能让整条产线停机。Agentic Center 的解法是：读取类操作不经确认、写入类操作需要用户明确确认，高风险写入（如批量写点、修改驱动参数）甚至需要输入操作员密码。随着系统运行积累足够的安全验证记录，可以逐步放开到“仅异常情况需确认”的默认执行模式。

自然语言运维不是要替代所有仪表盘——它解决的是信息检索快速定位和解释性对话的问题。在一个典型值班场景中，巡检人员从“先看哪个页面”到“直接说我想知道什么”，工作流从页面跳转变为语言对话。这背后是 Agentic Center 把10个 `@Tool` 编排成了一个可以理解业务语义的AI运维助手。

### 7.3.6 智能告警分析与数据洞察

规则引擎触发告警 → 运维人员接到通知 → 手动打开设备详情、翻最近日志、拉历史曲线 → 再凭经验判断原因 → 决策。这条链上平台数据并不缺，但散落在不同模块里，需要操作员自己把它们串成诊断线索。Agentic Center 用一条四阶段流水线接管了这种“拼接”工作，把碎片信息汇聚到 LLM 面前，让它一次性消费完再输出诊断建议。四阶段包括：告警接入与上下文汇聚 → RAG 检索增强 → LLM 生成诊断报告 → 结果推送与人工确认。

- **book-figure** 规格块开始
    - id: fig-7-9
    - type: flow-chart
    - title: 智能告警分析流程
    - purpose: 展示从告警触发到诊断推送的四阶段处理流水线，突出 RAG 检索与 LLM 生成的核心环节
    - layout: 水平流程图，从左至右依次排列阶段一至四，顶部标注触发事件
    - elements:
        - 阶段一：告警接入与上下文汇聚（矩形框，蓝色填充）
        - 阶段二：RAG 检索增强（矩形框，蓝色填充）
        - 阶段三：LLM 生成诊断报告（矩形框，蓝色填充）
        - 阶段四：结果推送与人工确认（矩形框，蓝色填充）
        - 触发气泡：告警到达（椭圆形，橙色填充，位于阶段一上方）
        - 数据源1: 告警事件流（圆角虚线框，位于阶段一下方）
        - 数据源2: 设备元数据中心（圆角虚线框，位于阶段一下方）
        - 数据源3: 时序数据库（圆角虚线框，位于阶段一/三下方）
        - 数据源4: 日志存储（圆角虚线框，位于阶段一下方）
        - 数据源5: 知识库/案例库（圆角虚线框，位于阶段二下方）
        - 判断节点：是否需要人工确认？（菱形框，黄色填充，位于阶段三与阶段四之间）
        - 自动执行分支：绿色实线箭头从菱形节点“否”出发指向阶段四底部
        - 人工确认分支：灰色虚线箭头从菱形节点“是”出发指向阶段四顶部
    - relationships:
        - 阶段一输出告警上下文（设备ID、实时值、事件日志） → 阶段二作为查询向量
        - 阶段二从知识库检索相似案例 → 输出检索结果到阶段三
        - 阶段三拼接上下文与检索结果 → 调用LLM生成结构化JSON报告
        - 阶段三输出报告 → 阶段四决策
        - 判断节点“是否需要人工确认？”：是 → 人工确认分支；否 → 自动执行分支
        - 所有阶段的数据读取通过虚线箭头指向对应数据源框
    - legend:
        - 实线矩形 = 处理阶段
        - 虚线圆角框 = 数据源
        - 菱形框 = 判断节点
        - 实线箭头 = 控制流方向
        - 虚线箭头 = 数据读取/写入流
        - 顶部气泡标记 = 触发事件
    - caption: 图7-9 智能告警分析流程：告警从触发到诊断推送的四阶段流水线。阶段二依赖持续建设的案例库；阶段四根据风险等级决定自动执行或人工确认；阶段三输出格式为JSON结构化报告。
    - render_notes: 水平布局，阶段一至四从左到右等宽排列，间距60px。阶段一上方为告警触发气泡（椭圆形，橙色填充，字体白色）。每个阶段下方有对应数据源虚线框（圆角矩形，浅灰色填充，边框虚线1.5px）。虚线箭头从数据源指向阶段框，箭头宽度1.2px灰色。阶段三与阶段四之间插入菱形判断节点（黄底黑字），分出两条路径：是（灰色虚线箭头，标注“人工”）；否（绿色实线箭头，标注“自动”）。阶段框字体12pt无衬线，数据源字体10pt。整体宽度800px，高度350px。
- **book-figure** 规格块结束

#### RAG 检索历史告警知识库

流水线第二阶段是 RAG 检索，它决定了诊断建议的深度。告警发生瞬间，Agent 把设备ID、告警类型、最近日志片段拼接成一条查询文本，到向量知识库中检索最相似的已处理案例。下面代码展示了两个核心操作：检索相似案例、写入新案例。

```java
@Component
public class AlarmKnowledgeRetriever {
    @Autowired private VectorStore vectorStore;

    public List<String> retrieveSimilarAlarmCases(String alarmContext, int topK) {
        SearchRequest request = SearchRequest.builder()
                .query(alarmContext).topK(topK).similarityThreshold(0.65)
                .build();
        return vectorStore.similaritySearch(request).stream()
                .map(doc -> String.format("案例来源: %s\n相似度: %.2f\n内容: %s",
                        doc.getMetadata().getOrDefault("case_source", "unknown"),
                        doc.getMetadata().getOrDefault("similarity", 0.0),
                        doc.getContent()))
                .collect(Collectors.toList());
    }

    public void storeAlarmCase(String caseId, String deviceType, String alarmType,
                               String description, String solution, String resolution) {
        String text = String.format("案例ID: %s\n设备类型: %s\n告警类型: %s\n描述: %s\n解决方案: %s\n处理步骤: %s",
                caseId, deviceType, alarmType, description, solution, resolution);
        Document doc = Document.builder().id(caseId).text(text)
                .metadata("case_source", "historical_alarm")
                .metadata("device_type", deviceType)
                .metadata("alarm_type", alarmType)
                .build();
        vectorStore.add(List.of(doc));
    }
}
```

检索参数 `similarityThreshold` 通常取 0.6~0.7 作为初始值（具体阈值需基于历史日志回放估算召回率与精确率的交叉点，而不是拍脑袋决定）。案例入库策略更关键：建议在每次告警工单关闭时自动触发 `storeAlarmCase`，不给运维人员增加记忆负担。

知识库效果高度依赖案例质量。启动初期案例不足，召回率偏低，诊断建议笼统。这没有捷径，知识库需要持续积累数月才能形成有效覆盖。实践中建议加入“案例质量反馈”机制：每次告警处理后，操作员对诊断建议标记“有用/无用”，写入案例元数据，用于后续优先级排序。字段不必复杂，一条布尔值即可。另外，案例库不能无限增长。设备更新、固件升级后，历史案例可能失效。建议设置案例老化策略，例如 180 天未引用的案例自动归档至冷存储。

**开发自查清单：**

- [ ] 确认 `similarityThreshold` 是否基于日志回放设置了初始值
- [ ] 确认 `topK` 与 `similarityThreshold` 组合不会召回全部低相似案例
- [ ] 确认 `storeAlarmCase` 在工单关闭流程最后一环被触发
- [ ] 确认案例元数据包含设备类型与告警类型，便于后续按维度筛选
- [ ] 确认已实现“有用/无用”反馈字段写入
- [ ] 确认已分配定时任务执行 180 天案例归档

#### 数据洞察：从诊断到趋势预测

告警诊断解决“当前发生了什么”。Agent 还能向前多看一步。假设场景：某温控器温度在 2:00–3:00 间从 62°C 匀速上升到 65°C，尚未触发 65°C 的高温阈值。Agent 执行例行数据巡检时，调用 `PointValueTool` 拉取最近 4 小时值，发现每 15 分钟上升约 0.7°C。按此速率，3:30 将超过 67°C。Agent 主动推送潜在告警提示：“温度持续上升，预计 30 分钟内触发高温告警。建议检查冷却系统或提前调整生产节拍。”（资料：[资料4]“异常到动作管道”）

此类预测性分析并不依赖复杂时序模型——时序数据库的聚合查询完成数据计算，LLM 仅负责趋势解读与建议生成。这带来一个重要权衡：聚合查询精度受采样频率和窗口大小影响，窗口太大可能平滑掉关键拐点，窗口太小则噪声过多。工程上一般按 15 分钟窗口做滑动聚合，覆盖过去 2–4 小时，并根据设备类型配置不同的报警趋势阈值。**设计权衡检查：** 聚合窗口的选择：窗口过短（<5分钟）引入噪声，过长（>1小时）延迟告警。建议按设备类型设定默认窗口，并允许运维人员通过配置文件覆盖。

#### 假设场景：一次完整告警分析（示意案例）

凌晨 3:14，Agentic Center 收到 PLC-01 离线告警，自动执行四阶段流程。3:15，运维人员看到对话框主动推送这个通知：

```
[主动推送] 检测到告警事件
告警设备：PLC-01（温控器）
类型：设备离线  触发时间：2025-03-15 03:14:22

Agent 初步诊断：
• 根因分析：最近5分钟无数据上报；同一交换机下其他设备通信正常，排除上游网络故障；3:10日志出现 "watchdog timeout"，可能与固件异常有关；最相似历史案例 ALM-20250108（PLC离线，固件挂起，远程重启恢复）。
• 影响范围：6个位号（3温度+3控制）停止采集。
• 建议处理步骤：1）远程重启 PLC-01；2）如失败安排现场巡检；3）下次维护窗口更新固件至 v2.3.6。

是否需要我执行步骤 1（远程重启）？
>> 确认执行
Agent 已调用 CommandTool 远程重启……完成。PLC-01 状态恢复“在线”，温度位号开始更新。
```

这条诊断不是模板填充的文本——上下文抽取、案例库检索、模型推理三者共同生成。运维人员看到后可免去二次排查，直接确认或执行。三个环节任一出问题，诊断都会跑偏。因此实际部署中建议为每个阶段单独设置超时和降级策略：阶段二 RAG 检索超时则降级为纯 LLM 推理，阶段三 LLM 生成超时则返回故障摘要供人工翻阅。

**延伸阅读：** 本章路线图部分提到的“异常到动作管道”，即利用时序聚合趋势提前推送潜在告警，在 [资料4] 中有详细说明。有关 Agentic Center 的 10 个内建工具（包含 `PointValueTool`），详见 7.3.4 节。告警功能与状态机降噪的完整设计，参考第 5 章。

## 7.4 多模型支持与私有化部署

### 7.4.1 支持多种大模型：GPT、Claude、DeepSeek、通义千问

运维第一天，用小陈的电脑配好GPT-4o，Agentic Center里对话流畅，工具调用精准。第二天安全合规通知落地：“所有设备位号数据禁止出网”。小陈把配置文件里 `spring.ai.openai.api-key` 换成 `spring.ai.ollama.base-url`，重启服务，模型变成了本地运行的Qwen2.5。聊天记录还在，工具照用，操作人员甚至没察觉到背后换了模型。

这种切换不是巧合，源自Agentic Center的架构设计选择。Spring AI 的 `ChatClient` 统一使用 OpenAI Chat Completions 协议，任何暴露该协议端点的模型提供商——公有云上或本地推理引擎（如 Ollama、vLLM）——都能被同一个接口接入（资料：[S10]）。差异集中在认证方式、端点URL和可选参数上，业务代码无需感知。

**适配器层的价值**

在没有统一接入层之前，每换一个模型等于重新实现HTTP调用、处理不同认证机制（API Key头、Bearer Token、Basic Auth），还要管理各自的超时和重试策略。Agentic Center 把这一切交给 Spring AI 的适配器层。开发人员只面对 `ChatClient` 接口，模型切换只需调整 `application.yml` 中的几行配置，工具层 `@Tool` 方法完全不受影响。这种解耦让平台能在几天内从云端模型迁到私有化模型，反之亦然。

**模型对比：场景决定选择**

没有哪个模型在所有维度上都占优。选型要结合成本、响应速度、中文支持、指令跟随能力和部署方式。表7-3给出定性倾向——具体参数以部署时实际测量为准，不做绝对排名。

| 模型 | 核心优势 | 适合场景 | 需注意的点 |
|------|----------|----------|------------|
| GPT-4o / GPT-5 | 指令遵循度高、推理链清晰、生态成熟 | 复杂诊断、多步骤任务规划、生成运维报告 | 成本较高；数据跨域传输需合规 |
| Claude 系列 | 长上下文处理强、拒绝率低 | 分析长时间跨度的日志、生成交接报告 | 需兼容代理适配 OpenAI 协议；中文能力需实测 |
| DeepSeek | 中文理解好、成本控制弹性大 | 国内运维团队、中文设备文档解析 | 复杂推理场景需对比测试；API 服务稳定性受网络影响 |
| 通义千问 (Qwen) | 中文语义强、支持函数调用 | 中文设备知识库检索、本地部署 | 多步骤工具调用需验证稳定性；官方 Ollama 模型与 API 行为略有差异 |
| Ollama 托管模型（任意开源 LLM） | 完全本地化、数据不出域 | 数据安全要求高的私有化部署 | 性能依赖 GPU；模型能力参差不齐，需选对参数规模与微调版本 |

（来源：定性分析，结合资料 [S1], [S10] 中的描述，非厂商精确数据。）

**配置切换实践**

在实际接入多个模型时，核心是在 Spring 中注册多个 `ChatClient` Bean，再在运行时通过 `@Qualifier` 或路由逻辑选择。以下给出一个配置示意（假设 `deepseek` 属性已自定义绑定）：

```yaml
# application.yml - 多模型配置示意
spring:
  ai:
    # 主力模型：GPT-4o
    openai:
      api-key: ${OPENAI_API_KEY}
      chat:
        options:
          model: gpt-4o
    # 备选模型：DeepSeek（兼容 OpenAI 协议）
    deepseek:
      api-key: ${DEEPSEEK_API_KEY}
      base-url: https://api.deepseek.com/v1
      chat:
        options:
          model: deepseek-chat
```

在代码中为每个模型创建专用 Bean：

```java
@Configuration
public class MultiModelConfig {
    @Bean
    @Primary
    public ChatClient gptChatClient(ChatClient.Builder builder) {
        return builder
            .defaultSystem("你是 IoT DC3 的智能运维助手。")
            .build();
    }

    @Bean
    @Qualifier("deepseekChatClient")
    public ChatClient deepseekChatClient(ChatClient.Builder builder) {
        return builder
            .defaultSystem("你是一个中文物联网运维助手，擅长处理设备查询。")
            .build();
    }
}
```

Agentic Center 的表 `dc3_model_provider` 已预留按会话切换模型的能力——同一个会话中可以动态路由到不同模型，例如简单查询走快速廉价的 GPT-4o mini，复杂诊断走推理能力更强的 GPT-5 或 Claude（资料：[S4]）。

**一个工程原则**

不要把模型选择变成“一刀切”。更好的做法是先接好两个差异较大的模型（如 GPT-4o 和 Qwen 本地版），运行一段时间收集延迟、成本、准确率数据，再根据结果调整路由比例。Agentic Center 的架构允许渐进式改进：添加新模型只是多一个 `ChatClient` Bean，不会破坏现有链路。

这种渐进式演进也呼应了全章从 Copilot 到 Agent 的演化路径：最开始，平台可能只接一个模型作为辅助查询工具；当多模型路由成熟后，模型自己能根据上下文决定用哪个“大脑”来处理任务，Agent 的自主性就往前推了一步。

---

**book-figure** = 规格块开始  
- **id**: fig-7-11  
- **type**: layered  
- **title**: 多模型统一接入架构  
- **purpose**: 展示 Agentic Center 通过 Spring AI 适配器层同时接入多个模型提供商的架构，强调切换仅需修改配置，不影响业务代码  
- **layout**: 自上而下的分层架构图，顶层为统一聊天界面，底层为外部模型提供商  
- **elements**:  
  - 顶层：用户 → 统一聊天界面（REST API）  
  - 中层：Spring AI 适配器层（`ChatClient` Bean）—— 统一接口，屏蔽模型差异  
  - 下层：模型连接配置（`application.yml`）—— 可配多个 API 端点、密钥、模型名  
  - 最底层（外部）：GPT-4o/GPT-5（OpenAI 端点）、Claude（兼容代理端点）、DeepSeek、通义千问、Ollama 本地模型、vLLM 推理引擎  
  - 左侧注释框：`dc3_model_provider` 表 —— 支持按会话切换模型；未来可扩展基于规则的路由逻辑  
- **relationships**:  
  - 用户请求经 REST API 到达 Agentic Center，由 Spring AI 适配器层转发至下层配置的模型提供商  
  - 每个模型提供商通过实线箭头连接适配器层，表示协议兼容  
  - `dc3_model_provider` 表以虚线箭头指向适配器层，表示运行时可读取该表来动态选择模型  
- **legend**:  
  - 实线矩形：系统组件或层  
  - 虚线矩形：外部模型提供商  
  - 实线箭头：请求/数据流方向  
  - 虚线箭头：可选/扩展流方向  
  - 矩形内文字：该层的核心抽象或配置  
- **caption**: 图7-11 多模型统一接入架构。用户请求经统一聊天界面到达 Agentic Center，Spring AI 的 `ChatClient` 作为适配器层将请求转发给任意兼容 OpenAI 协议的模型提供商。切换模型只需修改下层配置，不触碰业务逻辑。数据库表 `dc3_model_provider` 预留了按会话选择不同模型的能力，为多模型自动路由奠定基础。  
- **render_notes**: 采用分层呈现，顶层为一个宽水平条表示“统一聊天界面”，下方紧接三个堆叠矩形：第一层标注“Agentic Center REST API”，第二层高亮框标注“Spring AI ChatClient”，第三层标注“模型连接配置（application.yml）”。第三层下方引出五个虚线矩形，分别代表 GPT、Claude、DeepSeek、Qwen、Ollama，每个矩形内带简单图标或文字。左侧用一个虚线框标注“dc3_model_provider 表”，带箭头指向第二层表示运行时读取。整体采用蓝灰配色，关键层用亮色突出。  
**book-figure** = 规格块结束

### 7.4.2 私有化部署方案：安全与隐私考量

小陈在配置文件中只改了端点地址就完成了模型切换——这个操作背后隐含了一个重要的前提：本地必须有一个运行中的模型服务。私有化部署不是简单的“下载一个模型文件”，它涉及模型获取、推理引擎选型（Inference Engine）、硬件适配和运维管理四个维度。物联网场景中走私有化路线的驱动力，通常来自两条清晰的需求：数据主权和延迟可控。

**谁在要求私有化**

一家工厂的运维负责人说得直白：“设备位号数据就是我的工艺参数，出了厂区我睡不着觉。”在工业、能源和医疗领域，设备配置参数、运行曲线、故障模式是企业的核心资产。公有云大模型服务虽然承诺传输层加密，但模型推理发生在云上——每次请求的文本都会发送到模型提供商的数据中心。对于内部网络不与外网直连的生产环境，这条路根本走不通。

另一个驱动力是推理延迟。云端的模型调用包含网络传输时间。操作员说“关闭三号反应釜的进料阀”，如果模型需要先走外网再到云端推理，再返回指令，多出的数百毫秒在网络抖动时可能变成数秒。本地部署可以把推理延迟稳定控制在百毫秒以内，不受运营商网络状况影响。

**主流方案：Ollama、vLLM 与 LocalAI**

当前本地部署大模型的工具链已比较成熟。三个方案在物联网场景中最常用，各有侧重。

Ollama 的封装程度最高，一条 `ollama pull qwen2.5:7b` 命令就能拉起服务（资料：[S10]）。它的模型库丰富，主流大小的模型都有现成镜像。适合快速验证、单实例、低并发的场景——比如一个工厂只需要同时服务几个运维操作员。

vLLM 需要用户手动从 HuggingFace 拉取模型并指定路径，封装程度中等。它的优势是生产级的高吞吐和多实例高可用。当你要同时服务几十个操作员，或者把推理能力开放给外部 Agent 调用时，vLLM 的连续批处理（Continuous Batching）和 PagedAttention 机制能把 GPU 的利用率压榨到极限。

LocalAI 提供与 OpenAI API 完全兼容的接口，在容器化部署上更灵活。它对模型格式的宽容度更高——同一个部署可以同时加载不同厂商的模型。适合需要在同一台机器上运行多个异构模型的场景。

三个方案都提供 OpenAI 兼容端点，这正是 Spring AI 依赖的协议标准（资料：[S10]）。对 Agentic Center 来说，换推理引擎只需改 `base-url`，与切换云端模型没有架构差异。配置示例：

```properties
# application.properties（示意）
spring.ai.ollama.base-url=http://localhost:11434
spring.ai.ollama.chat.model=deepseek-r1:7b
# 替换为 vLLM 或 LocalAI 时，改这一行即可：
# spring.ai.openai.base-url=http://localhost:8000/v1
```

**硬件是现实约束**

GPU 资源是大多数团队面对的门槛。不同参数规模的模型对显存需求差异明显。以典型7B参数规模的模型为例，在消费级GPU上可以正常运行，但实际能跑多快、能支持多长的上下文序列，取决于量化精度和序列长度。更大参数规模的模型（例如达到数十亿参数级别），对显存和内存的要求会显著提高。当模型参数量超过单卡容量时，需要多卡并行或 CPU Offloading——把部分层放到 CPU 内存中，牺牲推理速度换取可用性。Ollama 和 vLLM 都支持这种技术。在 IoT 数据查询场景中，一次推理 3～5 秒的延迟通常可以接受，远好于完全无法部署。

**混合模式：分层决策，不二选一**

不是所有请求都需要私有化。小陈后来采用的方案是混合路由：简单的设备状态查询走本地 DeepSeek，响应快且数据不出域；复杂的故障根因分析走云端 GPT-4o，利用更强推理能力；涉及工艺参数的敏感查询再回本地。Agentic Center 的 `dc3_model_provider` 表支持配置多个提供商并可按会话选择模型（资料：[S4]）。实现混合路由只差一个路由逻辑：

```java
// 示意代码：按请求特征选择模型后端
public ChatClient selectModel(ChatRequest request) {
    if (request.containsSensitiveTags()) {
        return ollamaChatClient; // 敏感数据，走本地
    }
    if (request.isSimpleQuery()) {
        return ollamaChatClient; // 低延迟优先
    }
    return openAiChatClient; // 复杂任务，走云端
}
```

这套做法把一个看似二选一的问题，变成了可分层调控的决策。

**工程检查清单：开始私有化部署前**

1. 确认模型参数规模和所需显存估算，核对服务器 GPU 配置（参考模型发布页的推荐要求）。
2. 选择推理引擎：Ollama 适合快速验证，vLLM 适合生产高吞吐，LocalAI 适合异构模型共存。
3. 拉取模型镜像并验证 OpenAI 兼容端点可用。
4. 修改 Agentic Center 配置文件的 `base-url` 指向本地推理服务。
5. 验证工具调用链是否完整：发一条“查询所有离线设备”的测试消息。
6. （可选）部署混合路由逻辑，按查询类型和敏感度分级分流。

私有化不是全有或全无的选择。用对方法，可以在数据主权、响应速度和模型能力之间找到自己的平衡点。

![图7-13 私有化与混合部署架构](../figures/chapter-07/fig-07-13.png){width=15cm}

*图7-13 展示私有化部署中 Agentic Center 与本地/云端推理引擎之间的路由关系。*

## 7.5 从 Copilot 到 Agent：物联网运维的范式转移

### 7.5.1 Copilot 模式：辅助人类操作

运维人员坐在工位前，面前开着一个聊天窗口。他打了一行字：“查一下昨天凌晨三点二号产线哪台设备离线了。”几秒钟后，窗口里返回一条结构化回答：设备名称、离线时间、持续时长、最后上传的位号值。如果他想进一步处理，比如远程重启那台设备，他需要自己打开设备管理界面去执行。

这套交互模式就是 Copilot 模式——大模型充当一个有问必答的参谋，但不碰操作面板。这和微软 Copilot、GitHub Copilot 背后的设计理念一致：模型补充人的能力边界，但不替代人的最终判断。参谋提供情报和行动建议，但不握方向盘。设备开关、参数调整、驱动启停这些写操作，全部留给人工通过传统界面或脚本来完成。

**Copilot 的核心设计原则**：回答可以很精确，但执行的最后一步门槛留给人类。这在物联网运维中有很现实的理由——运维人员需要确认模型给出的操作建议在自己理解范围内，而不是让模型直接修改系统状态。一位经验丰富的运维工程师表达得很直接：“模型可以帮我查，但别替我按确认。数据是死的，判断错了还有机会改；设备控制错了，产线停了就是事故。”

在 IoT DC3 的场景里，Copilot 模式对应的是把大模型当作**增强版搜索引擎和日志分析器**。操作员问“三号反应釜温度有没有超限”，Agentic Center 调用 `PointValueTool` 拿到实时位号值，然后返回当前值、阈值、是否已触发告警。回答到这里就停了。要不要调参数、怎么调、什么时候调，操作员自己拿主意。

这种模式最直接的好处是**低风险、快上手**。运维团队不需要马上信任模型能够正确执行设备指令——信任需要时间积累——但可以先用对话的方式把数据查全、把异常定位到。一家工厂可能第一天只让 Copilot 查温度，第二天让它查频率，过了一周才让它试写一条简单的位号值。每一级的信任都是通过实际输出积累的。

Copilot 模式也有明确的边界。它**不主动执行任何操作，也不处理因果链超过两步的多任务**。比如“温度高了—检查冷却水阀门—如果关闭则打开—三分钟后复查”——这种序列需要 Agent 模式才能处理，Copilot 只会逐条回答。运维人员需要自己走通这四步，每步再问一次模型，人工拼接上下文。

下表把 Copilot 和下一节要展开的 Agent 模式做了粗粒度对比，方便读者先在心里建立一杆标尺。

**表 7-7 Copilot 与 Agent 的关键差异**

| 维度 | Copilot 模式 | Agent 模式 |
|------|-------------|-----------|
| 决策方式 | 建议由人执行 | 模型自主决策，必要时征求确认 |
| 执行粒度 | 单次查询或单步指令生成 | 多步任务规划、顺序执行、状态监控 |
| 风险边界 | 低——模型不走 API 写操作 | 中到高——模型可直接调用读写接口 |
| 适用场景 | 数据查询、日志检索、故障定位 | 自动修复、参数调优、批量运维 |
| 运维人员角色 | 操作主体，模型是辅助 | 监督者，模型是执行主体 |
| 信任前提 | 输出结果可被人工复核 | 需要充分的灰度验证与断路机制 |

两种模式不是谁取代谁的关系，而是同一平台在不同信任阶段的不同服务形态。Copilot 模式是走向 Agent 模式的第一级台阶——运维团队先习惯让模型帮忙看数据，确认它的分析可信，再逐步开放权限让它动手。

一个具体的 Copilot 工作情形可以让概念更实在。假设运维人员想排查一次夜间设备离线的原因：

```
操作员： "看看昨晚两点到三点之间，一楼配电柜的 UPS 状态。"
Agentic Center (Copilot)：
  -> 调用 DeviceTool 定位设备
  -> 调用 PointValueTool 读取对应时间段位号值
  -> 返回："昨晚 02:14:23 UPS 切换到电池供电，02:18:05 恢复主电。
          主电在 02:14:20 有 3 秒中断。无后续告警。"
操作员： "那把我查到的结果生成一条交接班备注。"
Agentic Center：
  -> 返回："02:14 主电闪断导致 UPS 启停，恢复后无异常。
          建议关注配电柜主电源接触器。"
操作员： "好的。下一步我想让它自动处理：如果下一次主电闪断超过 5 秒，自动切到柴油发电机。"
```

最后这句操作员的设想，恰恰是 Copilot 力不能及、需要 Agent 模式来承接的命题。从 Copilot 到 Agent 的阶梯怎么搭——信任怎么验证、权限怎么收回、异常怎么兜底——这些设计策略放在下一节展开。

### 7.5.2 Agent 模式：自主决策与执行

Copilot 模式把执行按钮留在人手里，Agent 模式则把这个按钮交给了模型——运维人员只需要给出目标，Agent 自主规划步骤、依次调用工具、监控执行结果，直到任务完成或遇到无法处理的障碍。这不是简单的功能升级，而是物联网运维范式的根本变化：从“人用模型查数据”变成了“模型替人去干活”。

**Agent 的核心工作循环**是“感知 — 规划 — 执行 — 反馈”的闭环。当操作员在 Agentic Center 中提交一个目标（比如“检查二号车间的网络连通性，如果发现设备离线则尝试重启”），Agent 首先调用 `DeviceTool` 查询该车间所有设备的在线状态，感知当前系统状况。接着，它将任务分解为子步骤——识别离线设备、检查离线持续时长、判断是否需要重启。规划完成后，Agent 逐一调用 `CommandTool` 执行设备重启指令，每执行一步都读取返回结果，确认设备是否恢复在线。如果某台设备重启后仍然离线，Agent 会标记异常，记录失败原因，并继续处理下一台设备，最后汇总一份执行报告给操作员。

这个循环依赖两个前提条件。第一个是**工具集合的完备性**——Agent 需要足够的“操作手柄”才能完成任务分解。IoT DC3 的 Agentic Center 内置 10 个 `@Tool` 工具，覆盖设备、驱动、点位、命令、事件等全部领域对象（资料：[S9]）。这意味着 Agent 面对“排查最近一小时温度超限的设备并生成干预建议”这类复合指令时，可以自主调用 `PointValueTool` 获取实时数据、调用 `DeviceTool` 关联设备元信息、调用 `EventTool` 查询历史告警，最后组合成一份结构化输出。若缺少任何一个工具，任务就会卡在某个环节。

第二个前提是**信任机制的建立**。Agent 自主执行的风险比 Copilot 高一个数量级——模型一个错误规划可能导致批量设备误动作。IoT DC3 的设计采用三层安全阀：

*   **操作日志审计**：每一次工具调用、每一次写入操作的入参和返回结果都会被完整记录，事后可以复现任意 Agent 会话的全链路。
*   **人类审批节点**：高风险操作（如批量写入设备参数、启停关键设备驱动）会被拦截，等待操作员在界面上确认后才能放行（资料：[S6]）。审批条件按照风险等级配置，例如对写位号值超过阈值的操作一律挂起，对只读查询则自动放行。
*   **回滚能力**：对于可逆的操作，Agent 需要先记录操作前状态（例如设备原参数快照），执行异常时能够发起反向操作恢复原值。对于不可逆的操作（如固件升级），Agent 不允许自动执行，必须由人工介入。

在这三层安全阀的保护下，Agent 的自主范围可以逐步扩大：先开放只读的查询工具，再开放低风险写操作（如修改非关键告警阈值），最后开放需要审批的高风险写操作。这种渐进式授权模式借鉴了工业控制的安全分级思想，确保任何误操作都不会超出预期边界。

以下是一个完整的假设场景，展示 Agent 从感知到执行再到汇报的完整链路：

> 凌晨 2:00，Agent 发现三号车间的若干台设备同时离线，持续超过 10 分钟。Agent 首先调用 `DriverTool` 检查驱动实例状态，确认驱动进程正常运行；接着调用 `DeviceTool` 对离线设备进行连通性测试，发现一部分设备网络不可达、另一部分设备可 ping 通但数据上报中断。Agent 自主执行“重启网络不可达设备的网口”操作（该操作被配置为低风险，自动放行），同时标记“数据上报中断但网络正常”的异常，生成一段自然语言描述：“三号车间三台设备离线（IP 不可达），已执行重启网口命令并等待恢复；两台设备网络正常但数据中断，可能与采集程序卡死有关，建议联系现场人员检查。详细日志见附件。”

![Agent 自主运维流程示意图](../figures/chapter-07/fig7-7.png){width=15cm}

*图7-7 Agent 自主运维流程示意图。图中虚线框表示信任机制层，涵盖操作日志审计、人类审批节点和回滚能力。红色箭头表示高风险操作需要等待人工确认，绿色箭头表示低风险操作自动执行。Agent 在完成报告后仍可通过持续监控循环重新感知系统状态。*

Agent 模式并非要完全取代 Copilot 模式，而是提供了另一种工作方式的选择。对于经验丰富的运维工程师，Copilot 模式依然有价值——他只需要模型提供信息，自己做出决策。但对于夜间值班、快速响应、例行巡检等场景，Agent 模式能显著提升效率。实际部署时，运维团队可以根据任务风险等级和自身信任程度，为不同任务配置不同的模式偏好，甚至在同一会话中混合使用：先通过 Copilot 模式验证方案，再切换到 Agent 模式让模型自主执行已批准的步骤。

### 7.5.3 演进路径与工程实践建议

从 Copilot 到 Agent 的迁移不是一刀切的版本升级，而是一个渐进的信任建立过程。操作员不会在第一天就允许模型自主重启设备群，运维团队也不会一夜之间从告警日志转移到对话窗。合理的演进需要分阶段推进，每个阶段都有明确的边界条件与撤回机制。

**第一阶段：Copilot 辅助查询与脚本生成。** 这一阶段模型只读不写，扮演一个对平台 API 了如指掌的“资深文档助教”。操作员用自然语言提问，模型调用 `DeviceTool`、`PointValueTool`、`PointTool` 等只读工具，返回查询结果；或者生成一条完整的工作指令——一个 `curl` 命令片段、一段平台 CLI 脚本、一个平台规则的 JSON 配置。操作员确认后手动执行。这是 Agentic Center 的最基础模式：先让操作员看到模型可靠，再逐步放开权限。典型场景如：“列出最近 24 小时温度超过阈值的所有位号，并生成告警规则模板。” 此阶段不涉及任何写入操作，工具白名单里只有只读工具，`ToolContext` 中的租户上下文使每次调用都经过完整鉴权，与常规 API 调用无异（参见第 2 章四层架构）。

**第二阶段：有限自主的 Agent。** 在特定范围、固定场景内允许模型自主执行。典型场景是**自动告警处理**：当 `EventTool` 检测到一台设备离线超过设定的持续时间后，Agent 自动调用 `DeviceTool` 查询设备详情、`PointValueTool` 检查关联点位的最新值（比如电压、温度），并将诊断结果、建议动作推送给人操作员。操作员只需点一次“确认”或设置一条自动放行的规则。这个阶段的 Agent 有明确的目标边界——比如“只处理离线告警，不涉及驱动变更”。它的每一步工具调用都被记录在会话日志中，任何风险动作（如重启设备、写入控制点位）都需要人工审批。工程上需要在 `dc3-center-agentic` 配置一个“场景白名单”，只有注册过的预设场景（如“检测离线大于 30 分钟”）才能激发 Agent 的自主执行链。

**第三阶段：全自治 Agent。** 经过前两个阶段的运行积累，运维团队对 Agent 的行为模式有了充分了解，可以逐步收窄人工确认的范围，直到多步运维任务完全交由 Agent 自主完成。第三阶段的 Agent 通常配合 **编排能力**运行：它接收一个长期目标（如“确保二号车间的平均温差不超过 2 度，连续检测到偏差自动调整风机转速”），自主规划、执行、监控、调整。这是当前 Agentic Center 路线图上的下一个前沿——参考资料中提到的“异常到动作管道”和“定时健康报告”即属于此类（资料：[S4]）。但即使到这一阶段，也并非所有场景都适合全自治——高风险动作（如切换主备电源、写入设备固件）仍然保留人工确认，在 `dc3-center-agentic` 中通过高风险工具白名单控制，该白名单可在 `dc3_model_provider` 表中按租户单独配置。

这三个阶段的推进必须有配套的工程措施：

- **监控与审计**。Agent 的每一次工具调用都应该被记录在 `agentic_session_detail` 表中，包含调用时间、工具名称、输入参数、返回结果、耗时。操作员能随时回溯 Agent 的行为链路，用于事后复盘或调试。Spring AI 的 `ToolCallback` 拦截器可自动采集这些信息。
- **灰度发布与分租户开关**。不应在一个生产环境中全局切换 Agent 模式。可以在某个测试租户下先开启全自治，运行一周稳定后再逐步开放到更多租户。`dc3_tenant` 表中可增加 `agent_mode` 字段，取值 `copilot_only`、`semi_autonomous`、`full_autonomous`，平台根据租户级配置加载不同的 Tool 白名单和审批策略。
- **回滚机制**。Agent 的每一个写入操作必须可逆。例如，Agent 修改了设备点位值，平台需要记录修改前值，并提供一个"撤销"入口——通常通过 `CommandTool` 的版本化操作实现，将每次修改的 before/after 快照存入 `point_value_history` 表。
- **人工覆盖开关**。当操作员发现 Agent 的行为不符合预期时，可以直接在会话中发出“停止”指令，或者通过管理界面一键暂停该租户下的所有 Agent 自主操作。Agent 的 `TaskExecutor` 实现应支持中断信号监听，收到停止指令后立即中止当前任务链并回滚已执行的写入操作。

下图概括了三个阶段在自主程度、人工介入点、风险控制方式上的差异，以及操作员信任度的递进关系。

![IoT DC3 Agentic Center 的 Copilot 到 Agent 三阶段演进路线](../figures/chapter-07/fig-7-5-3-1.png){width=15cm}

*图 7-5-3-1: IoT DC3 Agentic Center 三阶段演进路线示意。自主程度逐步提升，但人工确认点从未消失，只是从“每步确认”转变为“关键节点确认”。*

一句话总结这条演进路径：**先让模型证明自己能看对，再证明自己能想对，最后才交给它去做对。** 每向前一步，都给操作员一个可以提前撤回的缓冲区。Agentic Center 的架构从第一天就为这三个阶段做好了准备——它的会话持久化、工具级别的高风险标记、按租户的模型路由配置，都直接对应到演进路径中的工程需求。操作员不需要在 Copilot 和 Agent 之间二选一，而是可以按场景、按阶段、按信任度逐步右移。

## 7.6 工程收束

### 7.6.1 实践清单与常见陷阱

把 AIoT Agent 从概念推入生产，技术选型与架构设计只是起点。真正的工程地狱藏在细节里：模型选错了回答不了专业问题，工具参数写错了可能把设备写死，安全控制漏了一环则连日志里都留不下痕迹。以下清单直接指向工程师从“Copilot 起步、走向 Agent”时必须关照到的检查面，以及最常踩到的五个陷阱。

**表 7-2：AIoT Agent 工程实践清单**

| 检查领域 | 编号 | 检查内容 | 结果 | 备注 |
|----------|------|----------|------|------|
| **模型选型** | CHK-01 | 模型协议是否兼容 OpenAI Chat Completions？ | □通过 □未通过 | 若不兼容，需额外适配层。Spring AI 原生支持 OpenAI 协议（资料：[S10]） |
| | CHK-02 | 是否在 `dc3_model_provider` 表中配置了至少两个稳定提供商？ | □是 □否 | 支持多模型切换与按会话选择。单一提供商存在服务中断风险（资料：[S10]） |
| | CHK-03 | 是否规划了简单查询与复杂诊断使用不同模型的路由策略？ | □是 □否 | 示意：简单查询用快速廉价模型，复杂诊断用推理模型，本地敏感查询用 Ollama 实例（资料：[S4]） |
| **工具设计** | CHK-04 | 每个 `@Tool` 方法的 `description` 和 `@ToolParam` 描述是否明确标注了参数单位、取值范围和典型示例？ | □通过 □未通过 | 模型依赖描述决定是否调用工具。描述含糊会导致该调的没调、不该调的乱调。示意：描述“期望的转速值（单位：rpm，范围 0-3000）”比“期望值”减少模型猜测。 |
| | CHK-05 | 只读工具和写入工具是否在工具设计层明确分表？ | □是 □否 | 原理上只读工具在返回中注明“只读”，写入工具在描述中标明“写入操作+风险等级”。 |
| | CHK-06 | 写入工具是否在方法签名层之外做了参数范围校验和类型校验？ | □是 □否 | 示例：写入温度值应限制在 -50~150℃，超出范围直接抛异常拒绝。 |
| | CHK-07 | 每个工具是否包装了现有服务层方法，而非复制业务逻辑？ | □是 □否 | 逻辑一致性依赖单一定义源（资料：[S11]） |
| **安全控制** | CHK-08 | 是否所有工具调用都经过了鉴权中心和 RBAC 权限校验？ | □是 □否 | 模型拿不到比当前登录用户更多的权限，RBAC 规则与常规 API 一致（资料：[S9]） |
| | CHK-09 | 高风险操作（批量写、驱动配置变更、删除操作）是否设置了人工确认节点？ | □是 □否 | Agentic Center 内置高风险确认按钮（资料：[S6]） |
| | CHK-10 | MCP 端点是否启用了 OAuth 2.1 + 工具白名单 + 风险分级？ | □是 □否 | 外部 Agent 接入时，必须做 OAuth 授权方可暴露工具（资料：[S1]） |
| **日志与审计** | CHK-11 | 每次工具调用是否记录了租户 ID、操作时间、输入参数、返回状态和异常堆栈？ | □是 □否 | `ToolContext` 中已注入租户信息（资料：[S5]）；缺失日志会导致无法追溯故障 |
| | CHK-12 | 是否有实时监控看板展示工具调用成功率、超时率和异常率？ | □是 □否 | 示意图：监控样本建议选取自然周的数据，观察日间与夜间调用模式差异 |
| | CHK-13 | 是否有回滚机制能撤销已执行的写操作？ | □是 □否 | 对于不可逆操作（如删除驱动），至少应在日志中完整记录操作前后的状态，以便人工恢复 |
| **测试与部署** | CHK-14 | 是否先在“模拟模式”下运行工具调用覆盖多种典型场景？ | □是 □否 | 强制模拟模式：模型调用工具时只返回示例结果，不触发真实执行 |
| | CHK-15 | 是否先开放给内测租户（灰度发布）？ | □是 □否 | 建议至少选择低风险非关键设备为先导，观察生产周期 |
| | CHK-16 | 是否保留了从 Agent 模式紧急降回到 Copilot 模式的开关？ | □是 □否 | 紧急回滚由运维人员一键操作，不必重新部署服务 |
| **持续改进** | CHK-17 | 是否定期（每两周）审查模型调用记录，发现并修复工具误调用的 case？ | □是 □否 | 重点排查调用次数很少、但错误率很高的工具有无设计缺陷 |
| | CHK-18 | 是否测试了工具在 LLM 长上下文窗口内的表现？ | □是 □否 | 长对话中，模型可能遗忘工具描述；建议构造多轮长对话测试用例（示意样例：30 轮以上的对话可模拟严重遗忘风险） |

#### 常见陷阱

**陷阱 1：过度信任模型输出。** 工程师容易把模型的“一本正经”当作“绝对正确”。模型在调用函数时可能填写错误的参数，尤其当参数类型是其“猜测”而非真实值的枚举时。规避方式：所有写入操作的参数必须走两次校验——先验证参数在平台中是否存在（查 `Point` 表），再校验数值范围是否在物模型的 `min`/`max` 区间内（参见第 3 章物模型抽象）。平台逻辑永远优先于模型逻辑。

**陷阱 2：忽略故障回滚。** “设备指令已经下发”这件事本身没有撤回按钮。对于批量指令，模拟真实错误的覆盖率很重要。示意场景：运维人员要求“把所有风机的转速调至高速档”，模型调用 `CommandTool` 发送了多条指令，其中若干条因通信超时失败，剩下的已生效。如果没有回滚方案，现场需要人工逐台恢复。规避方式：对于批量写入，先走“模拟执行”模式识别潜在失败设备，再分批次下发（例如按小批量设备分组），每批确认结果后再决定是否发送下一批。

**陷阱 3：工具参数描述不严谨。** Spring AI 的 `@ToolParam` 标注本身不包含强校验逻辑。开发者必须在工具方法内部通过 `Assert.notNull` 或自定义验证器做二次约束。实践中常见的问题是：参数描述写成了“期望的转速值”，但没有明确单位（rpm 还是百分比），导致模型猜错。

**陷阱 4：忽略上下文窗口对工具可见性的影响。** 随着对话轮次增加，模型的前期 token 被挤压，早期的工具描述很可能被注意力机制遗忘（资料：[S8]）。工程上需要在每轮对话中都注入当前可用的完整工具列表，而不是只在第一轮注入一次。Spring AI 的 `ToolCallback` 机制默认支持在同一线程内每轮重新注册工具，但开发人员需要在长对话压力测试下确认工具仍然能被正确调用。

**陷阱 5：Copilot 与 Agent 的责任边界模糊。** 实操中常出现：用户希望模型能自主修复问题，但配置上只开放了只读工具、或者让模型生成脚本让用户手动执行——这本质上就是 Copilot 模式。切换 Agent 模式时，必须明确设定其执行范围（哪些设备、哪些操作可以自主）、自动确认阈值（无人工确认时能执行的最高风险等级）和回滚策略。不要寄希望于模型自行判断风险等级——那不是它的长项（资料：[S9]）。

### 7.6.2 延伸阅读与资源

本章的知识密度较高，跨了模型原理、工程框架与平台实操三条线。以下资源按“理论→框架→落地”的顺序组织，方便深入时对照查阅。

**官方文档与项目仓库**

- **Spring AI 官方文档**：覆盖 `ChatClient`、Function Calling、对话记忆的配置和核心 API，是集成时的第一案头手册（资料：[S10][S11]）。
- **IoT DC3 项目仓库**（GitHub: pnoker/iot-dc3）：`dc3-center-agentic` 模块的完整源码，内含 10 个内建 `@Tool` 工具类的实现与测试用例（资料：[S7]）。
- **LangChain 官方文档**：提供 RAG 和 Agent 循环的参考实现，可与 Spring AI 的实践对照。

**协议与标准**

- **MCP（Model Context Protocol）规范草案**：定义了模型与外部资源间的标准化接口。IoT DC3 的 MCP 网关是此规范的工程落地示例（资料：[S1][S4]）。
- **OpenAI Chat Completions API 规范**：Spring AI 的原生兼容协议。理解 `function_call`、`tools` 的协议细节，能有效排查工具调用失败问题（资料：[S10]）。

**核心论文与框架代码**

- **《ReAct: Synergizing Reasoning and Acting in Language Models》**：Agent 领域的奠基论文。本章 Agentic Center 架构中的思考‑行动循环源自此项工作。
- **Spring AI 官方示例工程**：GitHub 上 `spring-projects/spring-ai` 下的示范工程，提供可直接运行的最小原型。

**私有化部署**

- **Ollama**：本地模型部署的起点。支持 DeepSeek、Qwen 等模型的单机加载，暴露 OpenAI 兼容端点，适合敏感数据本地化验证（资料：[S4]）。
- **vLLM**：生产级推理加速方案，提供 PagedAttention 优化和连续批处理。

建议阅读顺序：先通读 ReAct 论文，理解 Agent 循环；再跟 Spring AI 官方文档写一个“查询设备温度”的 ChatClient 原型；然后啃 IoT DC3 的 Agentic Center 源码，重点看 `DeviceTool` 和 `PointValueTool` 的安全上下文注入方式。每步都能与本章内容对照验证。