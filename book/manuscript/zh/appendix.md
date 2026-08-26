# 附录

## A. 术语表

| 术语 | 英文 | 释义 |
|---|---|---|
| AIoT | Artificial Intelligence of Things | AI 与物联网深度融合，从被动连接到主动智能 |
| MCP | Model Context Protocol | Anthropic 2024 推出的 AI 与工具/数据源交互开放标准；2025 年 12 月捐赠给 Linux 基金会旗下 Agentic AI Foundation |
| Tool-Calling | Tool Calling | LLM 通过函数调用操作外部工具（如设备）的机制 |
| RAG | Retrieval-Augmented Generation | 检索增强生成，模型结合检索知识回答 |
| Agent | AI Agent | 能感知、推理、规划、执行的多步智能体 |
| 物模型 | Thing Model / Profile | 设备能力抽象（属性/服务/事件），屏蔽协议差异 |
| 位号值 | Point Value | 带语义的设备数据点（设备 ID+时间戳+单位+值） |
| Agentic Center | Agentic Center | IoT DC3 的智能决策中枢，基于 Spring AI |
| LPWAN | Low-Power Wide-Area Network | 低功耗广域网（NB-IoT/LoRa 等） |
| RedCap | Reduced Capability | 5G 轻量化（Rel-17），面向中端 IoT |
| TSFM | Time Series Foundation Model | 时序基础模型（TimesFM/Chronos 等），零样本预测 |
| 设备影子 | Device Shadow | 平台维护的设备期望/实际状态，解耦在线状态 |
| 边云协同 | Edge-Cloud Collaboration | 边缘实时+云端深算的分层协作 |
| RBAC/ABAC | Role/Attribute-Based Access Control | 基于角色/属性的访问控制 |
| MQTT | Message Queuing Telemetry Transport | 消息队列遥测传输，IoT 事实标准消息协议 |
| CoAP | Constrained Application Protocol | 面向受限设备的精简 Web 协议（RFC 7252） |
| LwM2M | Lightweight M2M | OMA 定义的轻量设备管理协议（基于 CoAP） |
| OPC UA | OPC Unified Architecture | 工业互操作应用层协议（IEC 62541） |
| QoS | Quality of Service | 消息传递语义：至多一次(0)/至少一次(1)/恰好一次(2) |
| 时序数据库 | Time Series Database | 面向时间戳数据的存储与聚合（TimescaleDB/InfluxDB 等） |
| DID | Decentralized Identifier | 去中心化标识符（W3C 标准），标识符由主体自主控制 |
| 联邦学习 | Federated Learning | 多方不上传原始数据协同训练模型的机制 |
| 数字孪生 | Digital Twin | 物理实体在数字空间的实时镜像与仿真 |
| ISA-95 | ISA-95 | 企业与控制系统集成的国际标准分层模型（L0–L4） |
| V2X | Vehicle-to-Everything | 车与车/路/网/人通信的总称（C-V2X/DSRC） |
| RSU/OBU | Roadside Unit / On-Board Unit | 路侧通信单元/车载通信单元 |
| 边缘计算 | Edge Computing | 在靠近数据源的一侧完成计算与决策 |

## B. 参考文献

1. 3GPP TS 22.261 — 5G 系统服务要求（含 IoT 场景）
2. 3GPP TS 36.300 — LTE/4G 系统架构（E-UTRA 总体描述）
3. 3GPP TS 38.300 — 5G NR 系统架构总体描述
4. 3GPP TR 38.875（RedCap 研究报告）/ TR 38.821（NTN 非地面网络研究报告）
5. CSA，*Matter Specification* — 智能家居统一应用层标准
6. OASIS，*MQTT Version 5.0* — 消息队列遥测传输协议
7. IETF，*RFC 7252（CoAP）* / *draft-ietf-oauth-v2-1（OAuth 2.1 草案，尚未定稿）* / *RFC 8628（设备授权流）*
8. Anthropic / Agentic AI Foundation，*Model Context Protocol (MCP) Specification* — AI 与工具交互开放标准
9. Spring 官方文档 — *Spring Boot 4.0（GA 2025-11）/ Spring Cloud 2025.1（GA 2025-11）/ Spring AI 2.0（GA 2026-06）* Reference
10. IoT Analytics，*State of IoT* — 全球物联网设备规模与产业数据
11. LoRa Alliance，*LoRaWAN L2 1.0.4 / 1.1* 与 *Regional Parameters RP-002-1.0.5（2025-10）*
12. IoT DC3 开源项目 — https://gitee.com/pnoker/iot-dc3 （全书贯穿案例）

## C. 索引

**协议与通信**：MQTT / CoAP / LwM2M / Modbus / OPC UA / NB-IoT / LoRa(WAN) / 5G(RedCap/NTN) / Wi-Fi / BLE / Zigbee / Matter / Thread / gRPC / REST

**架构与平台**：五层架构 / 智能层 / 微服务 / Gateway / Auth / Manager / Data / Agentic / 物模型 / 位号值 / 设备影子 / 时序数据库 / 消息队列 / 规则引擎 / 边云协同

**AI 与智能体**：大语言模型(LLM) / Agent / RAG / Tool-Calling / MCP / Spring AI / Agentic Center / 自然语言运维 / 异常检测 / 预测性维护 / TSFM / 端侧 SLM

**安全**：OAuth 2.1（IETF 草案）/ JWT / X.509 证书 / TLS 1.3 / DTLS / RBAC / ABAC / 多租户 / Prompt 注入 / PQC（后量子）

**应用场景**：工业物联网(IIoT) / 数字孪生 / 智慧城市 / 车联网(V2X) / 精准农业 / 区块链+IoT / 供应链溯源
