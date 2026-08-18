# 附录

## A. 术语表

| 术语 | 英文 | 释义 |
|---|---|---|
| AIoT | Artificial Intelligence of Things | AI 与物联网深度融合，从被动连接到主动智能 |
| MCP | Model Context Protocol | Anthropic 2024 推出的 AI 与工具/数据源交互开放标准 |
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

## B. 参考文献

1. 3GPP TS 22.261 / 36.300 / 38.300 — 移动通信系统架构与服务要求
2. 3GPP TS 38.875（RedCap）/ TR 38.821（NTN） — 5G 轻量化与非地面网络
3. CSA，*Matter Specification* — 智能家居统一应用层标准
4. OASIS，*MQTT Version 5.0* — 消息队列遥测传输协议
5. IETF，*RFC 7252（CoAP）* / *draft-ietf-oauth-v2-1（OAuth 2.1 草案）* / *RFC 8628（设备授权流）*
6. Anthropic，*Model Context Protocol (MCP) Specification* — AI 与工具交互开放标准
7. Spring 官方文档 — *Spring Boot 4.0 / Spring Cloud 2025.1 / Spring AI 2.0* Reference
8. IoT Analytics，*State of IoT* — 全球物联网设备规模与产业数据
9. LoRa Alliance，*LoRaWAN Specification 1.0.4 / 1.1*
10. IoT DC3 开源项目 — https://gitee.com/pnoker/iot-dc3 （全书贯穿案例）

## C. 索引

**协议与通信**：MQTT / CoAP / LwM2M / Modbus / OPC UA / NB-IoT / LoRa(WAN) / 5G(RedCap/NTN) / Wi-Fi / BLE / Zigbee / Matter / Thread / gRPC / REST

**架构与平台**：五层架构 / 智能层 / 微服务 / Gateway / Auth / Manager / Data / Agentic / 物模型 / 位号值 / 设备影子 / 时序数据库 / 消息队列 / 规则引擎 / 边云协同

**AI 与智能体**：大语言模型(LLM) / Agent / RAG / Tool-Calling / MCP / Spring AI / Agentic Center / 自然语言运维 / 异常检测 / 预测性维护 / TSFM / 端侧 SLM

**安全**：OAuth 2.1 / JWT / X.509 证书 / TLS 1.3 / DTLS / RBAC / ABAC / 多租户 / Prompt 注入 / PQC（后量子）

**应用场景**：工业物联网(IIoT) / 数字孪生 / 智慧城市 / 车联网(V2X) / 精准农业 / 区块链+IoT / 供应链溯源
