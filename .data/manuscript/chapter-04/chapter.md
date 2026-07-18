# 第4章 网络层通信技术

网络层负责把感知层采集的数据可靠送达平台层，并把指令下发回设备。它的核心挑战不是"某项协议多强"，而是**异构通信技术如何并存选型、以及协议碎片化如何统一接入**。本章先讲主流通信技术的选型决策，再讲协议碎片化痛点与统一接入层的解法，最后用 IoT DC3 的 Driver SDK 把这套架构落成可运行实践。

## 4.1 主流通信技术概览与选型

物联网通信技术门类多，但选型本质只有一个框架：**按场景在五个维度（距离、速率、功耗、成本、部署条件）上排序权重，再匹配技术**，而不是先选技术再倒推场景。下面按"广域低功耗、蜂窝宽带、室内短距"三类展开。

**NB-IoT（窄带物联网）**：工作在授权频段（运营商蜂窝），载波带宽仅 180kHz（一个 LTE 资源块），以深覆盖、低功耗、广连接见长。它适合**低频上报的固定资产**——智能水表、烟感、井盖、环保监测点，这类设备数据量小、几年不换电池、部署在运营商覆盖范围内。授权频谱意味着走运营商网络、付月租，但省去自建基站的麻烦。5G 的 mMTC（海量机器通信）能力主要继承自 NB-IoT/eMTC——二者作为 5G 物联网接入子集透传接入 5G 核心网。

**LoRa 与 LoRaWAN**：与 NB-IoT 走授权频谱不同，LoRa 工作在 Sub-GHz 免授权频段，用户可自建网关、不付月租。这里必须厘清一个常见误解：**LoRa 物理层（CSS 线性调频扩频调制）是 Semtech 持有核心专利的专有技术，从未开放标准化**；其上的 **LoRaWAN 网络协议（MAC/网络层）才是由 2015 年成立的 LoRa 联盟标准化、对外开放的部分**。LoRa 适合**无运营商覆盖或拒绝月租、需要自建可控网络的场景**——农场、矿区、园区。LoRaWAN 当前主线版本为 1.0.4 与 1.1（后者含漫游与安全增强）。值得一提的是，曾经与 NB-IoT/LoRa 三足鼎立的 Sigfox（超窄带专网路线）已于 2022 年破产、被新加坡 UnaBiz 收购，标志着专网 LPWA 路线式微，行业转向 NB-IoT/LoRaWAN 多技术并存。

**5G 与蜂窝演进**：5G 定义了三大场景——eMBB（增强移动宽带）、uRLLC（超可靠低时延，空口目标约 1ms、可靠性 99.999%）、mMTC（海量连接）。对物联网最重要的是两个 2024–2026 年的新进展：**5G RedCap（NR-Light，3GPP Rel-17）** 带宽收敛到 ≤20MHz、削减接收链路与载波聚合，填补了 NB-IoT/eMTC 与全功能 5G 之间的中段空档，瞄准可穿戴、工业无线传感器、车载等场景（Rel-18 的 eRedCap 进一步瘦身）；**3GPP NTN（非地面网络）** 在 Rel-17 为 NB-IoT/eMTC 增加原生卫星接入（IoT-NTN），并定义 NR-NTN（智能手机直连卫星），星链 Direct-to-Cell 已于 2025 年商用，对地广人稀、海洋、应急物联网补盲意义重大。再往前看，**6G（IMT-2030）** 已由 ITU-R 确立愿景（2023.11 M.2160），3GPP Rel-21 启动研究，目标 2030 商用，将整合 NTN、太赫兹与 AI 原生连接。

**室内短距：Wi-Fi、BLE、Zigbee 与 Matter/Thread**。三者各有定位：Wi-Fi 带宽高但功耗大，适合需要联网与视频的设备；BLE 超低功耗、支持 mesh 扩容，适合可穿戴与小型传感网；Zigbee 标准化互操作、mesh 生态成熟，适合楼宇传感。Wi-Fi 这几年也在向物联网渗透——Wi-Fi 6（802.11ax）引入 OFDMA 与目标唤醒时间（TWT）降功耗、Wi-Fi 7（802.11be）扩展能力，HaLow（802.11ah，Sub-1GHz）则专为远距低功耗物联网设计。但室内短距长期被碎片化困扰：设备跨品牌不互通。**Matter**（CSA 连接标准联盟——原 Zigbee 联盟，2021 年更名——于 2022 年 10 月发布的统一应用层标准）与 **Thread**（IPv6 over 802.15.4 的 mesh 网络层）正在改变这一点：到 2026 年，Matter 已整合 Zigbee/BLE/Wi-Fi 接入，成为 Apple/Google/Amazon 共同遵守的智能家居事实标准，直接缓解了困扰行业多年的碎片化。

**选型建议**：用一张五维雷达图（距离/速率/功耗/成本/部署）把候选技术与场景需求对照。NB-IoT/LoRa 解决广域低功耗（前者走运营商、后者自建），5G（含 RedCap/NTN）覆盖中段到宽带，Wi-Fi/BLE/Zigbee 解决室内短距，Matter/Thread 收敛智能家居碎片化。没有万能协议，只有最匹配场景的组合。

```book-figure
id: fig-4-01
type: matrix
title: 图4-01 物联网无线技术选型雷达图
purpose: 用五维（距离/速率/功耗/成本/部署）雷达图对比主流通信技术的选型定位
layout: 五维雷达，各技术（NB-IoT/LoRa/5G RedCap/Wi-Fi/BLE/Zigbee）多边形叠加
caption: 图4-1 选型雷达图：NB-IoT/LoRa 在距离与功耗占优，5G/Wi-Fi 在速率占优，BLE/Zigbee 在成本与部署占优；按场景权重选技术组合。
render_notes: 五维雷达图 SVG，各技术不同色多边形叠加，轴标签距离/速率/功耗/成本/部署，底部图例。
```

## 4.2 协议碎片化与统一接入的必要性

通信技术多还不是最大痛点，**协议碎片化**才是。一个工厂里可能同时有 Modbus、OPC UA、MQTT、CoAP、BACnet 及各种私有协议，每种协议的帧格式、寻址、语义都不同。

碎片化有三个结构性原因：一是技术出身差异（Modbus 源自工控、MQTT 源自消息中间件、OPC UA 源自工业互联，设计哲学不同）；二是应用层协议栈差异（同样的"温度"，Modbus 是寄存器地址、MQTT 是 topic、OPC UA 是节点 ID）；三是模组厂商各自加私有协议。结果是：每接入一款新设备就要写一套协议适配器，跨协议的业务逻辑互相耦合，运维债务越积越重。

统一的出路是**统一接入层**——在设备与平台之间架一层抽象，把协议差异封装在底层，向上提供统一的设备模型与数据接口。它提供四项核心能力：**协议转换与适配**（对接各种协议）、**统一设备模型**（用物模型屏蔽协议差异）、**热插拔与动态加载**（加协议不用重启）、**安全保障**（接入鉴权与隔离）。有了它，平台层不再关心设备说什么协议，只面对统一的位号值流。

```book-figure
id: fig-4-02
type: architecture
title: 图4-02 多协议设备接入困境与统一接入层
purpose: 展示协议碎片化痛点及统一接入层如何收敛
layout: 左侧多协议设备（异构），右侧平台，中间统一接入层
caption: 图4-2 没有统一接入层时，每种协议都要单独适配（N×N 耦合）；引入统一接入层后，协议差异封装在底层，平台只面对统一设备模型与位号值流。
render_notes: 架构 SVG，左侧异构设备（多协议色块）、右侧平台、中间统一接入层（蓝带），标注协议转换/统一模型/热插拔/安全四能力。
```

## 4.3 统一接入层设计原则

统一接入层通常分四层：**协议泛化层**（对接具体协议驱动）、**连接管理**（建连、心跳、重连、会话）、**数据解析**（协议帧→标准位号值）、**设备抽象**（标准位号值→物模型）。调用关系是单向下行（平台→驱动）与异步回调上行（设备数据→平台），避免双向耦合。

其中**物模型三要素**是关键（第 3 章已介绍）：属性（状态量）、事件（异步通知）、服务（可调操作）。它的价值是把"模型"与"协议"分离——上层只面向物模型编程，协议变化封进底层适配器。理论上 N 种协议两两互通需要 N×(N-1) 套翻译，引入物模型作为单一锚点后降为 2N 套（各协议↔物模型），复杂度大幅下降。

具体实现用**适配器模式**：定义一个稳定的驱动接口（init/connect/read/write/keepAlive/isConnected 等），每种协议写一个适配器实现它，新增协议就是新增适配器，上层接口不变。这是把"变化"隔离在薄薄一层里的经典工程手法。

```book-figure
id: fig-4-03
type: layered
title: 图4-03 统一接入层四层架构
purpose: 展示协议泛化/连接管理/数据解析/设备抽象四层及物模型锚点
layout: 自下而上四层，物模型作为贯穿锚点
caption: 图4-3 统一接入层四层：协议泛化对接驱动、连接管理管会话、数据解析转位号值、设备抽象映射物模型；物模型是上下层的单一锚点。
render_notes: 四层架构 SVG，自下而上四色层，右侧物模型竖条贯穿，层间下行调用+上行回调箭头。
```

```book-figure
id: fig-4-04
type: architecture
title: 图4-04 物模型把 N×N 耦合削成 2N
purpose: 展示物模型作为单一锚点降低协议互通复杂度
layout: 左 N×N 全互联，右 各协议→物模型 星形
caption: 图4-4 无物模型时 N 种协议两两互通需 N×(N-1) 翻译；引入物模型作锚点后降为 2N（各协议↔物模型）。
render_notes: 对比 SVG，左侧 N 节点全连线（密集）、右侧 N 节点星形连中心物模型，标注复杂度 N²→2N。
```

## 4.4 IoT DC3 与 Driver SDK

IoT DC3 是统一接入层的产品级落地样本。它内置约 28 种协议驱动（Modbus、OPC UA、MQTT、CoAP、BACnet、BLE 等，截至写作时点），每个驱动是一个**独立微服务**。驱动通过 gRPC 与 Manager 同步元数据，通过 RabbitMQ 收发点位命令、位号值和状态事件——增加协议就是增加一个驱动模块，不需要把协议细节写进中心服务。

驱动开发的载体是 **Driver SDK**，但当前源码并不存在 `AbstractDriver` 基类。SDK 把能力拆成小粒度服务契约：`DriverRegisterService.initial()` 在启动阶段组装驱动、租户和属性元数据，并由 `DriverClient.driverRegister()` 通过 gRPC 向 Manager 完成**业务注册**；`DriverReadService`、`DriverWriteService` 负责校验元数据并把实际读写委托给协议实现；协议驱动实现聚合接口 `DriverCustomService`，或按需实现它组合的 `DriverLifecycle`、`DriverProtocol`、`DriverHealth` 等能力接口。核心入口可概括为：

```java
public interface DriverRegisterService {
    void initial();
}

public interface DriverReadService {
    void read(Long deviceId, Long pointId);
}

public interface DriverWriteService {
    boolean write(Long deviceId, Long pointId, String value);
}
```

这里的“注册”是驱动向 Manager 提交业务元数据，不是向 Nacos、Eureka 一类服务注册中心登记实例。服务寻址使用固定服务名并允许环境变量覆盖；驱动的独立部署能力来自模块边界、统一 SPI、gRPC 与 RabbitMQ 契约，而不是所谓“注册中心热插拔”。这套 Driver SDK 机制是**第 14 章 IoT DC3 实战开发的入口**。

```book-figure
id: fig-4-05
type: architecture
title: 图4-05 Driver SDK 服务契约与驱动实现
purpose: 展示 Driver SDK 的启动注册、协议读写、消息发送三类真实契约，以及协议驱动与 Manager、RabbitMQ 的协作关系
layout: DriverInitRunner 启动编排→DriverRegisterService 经 gRPC 调用 Manager；DriverReadService/DriverWriteService→DriverCustomService 协议实现；DriverSenderService→RabbitMQ→Data
caption: 图4-5 Driver SDK：启动阶段经 DriverRegisterService 向 Manager 同步业务元数据，运行阶段由 DriverReadService/DriverWriteService 调用协议实现，并由 DriverSenderService 经 RabbitMQ 上报位号值与状态事件。
render_notes: 架构 SVG，左侧为 DriverInitRunner 与 SDK 服务契约，中间为 Modbus/OPC UA/MQTT 等 DriverCustomService 实现，右侧并列 Manager（gRPC）与 RabbitMQ/Data（异步消息），标注"业务注册≠服务注册中心"。
```

## 4.5 工程收束

网络层的核心判断带走几条：选型按五维（距离/速率/功耗/成本/部署）匹配场景，NB-IoT/LoRa 解决广域低功耗（授权 vs 自建），5G RedCap 补中段、NTN 补盲、6G 在路上，Wi-Fi/BLE/Zigbee 解决室内短距、Matter/Thread 收敛智能家居碎片化；协议碎片化是物联网工程的核心痛点，统一接入层（四层架构 + 物模型锚点 + 适配器模式）是公认的解法；IoT DC3 的 Driver SDK 以细粒度 SPI、gRPC 业务注册与 RabbitMQ 消息契约支撑独立驱动微服务，是第 14 章实战开发的入口。
