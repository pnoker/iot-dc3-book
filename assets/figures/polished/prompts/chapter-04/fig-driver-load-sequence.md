请按 architecture-diagram 技能的浅色出版印刷风格，重绘下面这张书籍插图。

硬性要求：
1. 输出 self-contained HTML，主体为 inline SVG；同时导出同名 SVG 与 PNG。
2. 使用 1800×900 白色画布、极淡网格、浅色填充、饱和描边、深色文字、圆角卡片和清晰箭头，图例置于主体边界外。
3. 节点短标签优先，解释写入 callouts；禁止“节点1/节点2/container/service/user”等占位词。
4. 每张图只表达一个主结论，主链路高亮，边界、层级、时序或决策关系必须一眼可读。
5. 中文字体使用系统无衬线字体栈；PNG 需适合 Word 印刷，文字不得重叠或过小。
6. 保持全书统一视觉语义：蓝=核心平台，青绿=边缘/接入，橙=AI/智能，紫=数据，红=安全/风险，灰=外部依赖。

图表 brief：
{
  "id": "fig-driver-load-sequence",
  "type": "sequence",
  "title": "图4-8 IoT DC3 驱动启动与业务注册时序",
  "purpose": "展示 Driver 从进程启动到 Manager 业务注册、协议初始化、RabbitMQ 队列监听和状态上报的真实顺序",
  "audience_takeaway": "展示 Driver 从进程启动到 Manager 业务注册、协议初始化、RabbitMQ 队列监听和状态上报的真实顺序",
  "visual_focus": "DriverInitRunner、DriverRegisterService、Manager(gRPC)、DriverCustomService、RabbitMQ 五个参与者；先业务注册，再协议初始化和调度初始化，最后监听命令并上报状态",
  "layout": "DriverInitRunner、DriverRegisterService、Manager(gRPC)、DriverCustomService、RabbitMQ 五个参与者；先业务注册，再协议初始化和调度初始化，最后监听命令并上报状态",
  "components": [],
  "connections": [],
  "regions": [],
  "callouts": [],
  "legend": [],
  "caption": "图4-8 驱动启动后先经 gRPC 向 Manager 同步业务元数据，再初始化协议资源与调度任务；运行时通过 RabbitMQ 收发命令、回执和状态。业务注册不等于服务注册中心。",
  "visual_constraints": [
    "浅色时序图，实线表示 gRPC 同步调用，虚线表示 RabbitMQ 异步消息；底部标注固定服务名、容器 DNS 与环境变量寻址。"
  ]
}
