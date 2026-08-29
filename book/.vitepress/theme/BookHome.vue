<script setup lang="ts">
import {computed} from 'vue'
import {useData} from 'vitepress'

const {page} = useData()
const isEnglish = computed(() => page.value.relativePath.startsWith('en/'))

const copy = computed(() => isEnglish.value ? {
  premise: {
    kicker: 'The question behind the book',
    title: 'Once a model can reason, how does it touch the real world safely?',
    description: 'In an industrial system, an answer cannot become an action directly. The field must first be observable, its signals must become trustworthy context, and every write must pass through an execution boundary.',
    items: [
      {index: '01', eyebrow: 'Observe', title: 'Make the physical world legible', description: 'Sensors, protocols, drivers, point values, and thing models turn fragmented field signals into stable platform data.'},
      {index: '02', eyebrow: 'Reason', title: 'Turn data into usable context', description: 'Data processing, rules, RAG, tools, and MCP give an agent the context it needs to understand a task and form a decision.'},
      {index: '03', eyebrow: 'Act', title: 'Put governance before execution', description: 'Identity, authorization, validation, policy, confirmation, recovery, and audit stand between model intent and a physical command.'}
    ],
    boundary: 'An LLM can interpret intent and orchestrate governed tools. Real-time control, safety interlocks, and fault protection still belong to deterministic systems such as PLCs and edge controllers.'
  },
  thesis: {
    kicker: 'The narrative spine',
    title: 'The platform does not disappear when agents arrive. It becomes their foundation.',
    description: 'The book follows one cumulative engineering path rather than treating industrial software, IoT, and AI as three unrelated topics.',
    stages: [
      {number: '01', tag: 'Starting point', title: 'Industrial software boundaries', description: 'SCADA, DCS, MES, and PLCs solve essential local and deterministic problems, but data silos and closed capability boundaries limit wider collaboration.'},
      {number: '02', tag: 'Platform base', title: 'Unified IoT data and capabilities', description: 'Multi-protocol access, thing models, cloud-edge collaboration, and platform data processing create a reusable digital base.'},
      {number: '03', tag: 'Decision layer', title: 'A governed Agent Runtime', description: 'Spring AI, RAG, tools, MCP, state, workflow, and audit bring probabilistic reasoning into an explicit engineering boundary.'},
      {number: '04', tag: 'Outcome', title: 'Bounded autonomy', description: 'The system can sense, reason, execute, verify, and recover without pretending that a model is a PLC or a safety system.'}
    ],
    formula: ['Reliable data', 'Governed tools', 'Deterministic execution', 'Traceable feedback']
  },
  journey: {
    kicker: 'One concrete walkthrough',
    title: 'One cooling-pump vibration alert, end to end',
    description: 'The full mechanism chain in a single real incident: from a cooling-pump vibration value arriving to one confirmed write. Each step is developed in Chapters 4–5, 7, 8, and 14.',
    steps: [
      {number: '01', title: 'Uplink & storage', description: 'The driver reports the vibration point value over MQTT; unit and timestamp land in the time-series store.', ref: 'Ch. 4–5'},
      {number: '02', title: 'Threshold alert', description: 'The rule engine lifts the excursion out of thousands of point values—deterministic logic holds the line first.', ref: 'Ch. 5'},
      {number: '03', title: 'Evidence, not guesswork', description: 'Through authorized tools the agent reads trend, load, and maintenance records—the evidence points to early bearing wear.', ref: 'Ch. 7'},
      {number: '04', title: 'A pending Action', description: 'Writes are never sent directly: a pending Action passes schema, permission, and risk checks first.', ref: 'Ch. 7–8'},
      {number: '05', title: 'Confirm & audit', description: 'After human confirmation a deterministic path executes; receipts and audit trails stay queryable.', ref: 'Ch. 8, 14'}
    ],
    note: 'Every step has a clear owner: data to drivers, alerts to rules, judgment to the model, actions to workflow, execution to deterministic paths.'
  },
  parts: {
    kicker: 'Three parts · fourteen chapters',
    title: 'Build the complete loop, layer by layer',
    description: 'Each part inherits the constraints established by the one before it. The engineering base is never discarded when the story reaches AI.',
    items: [
      {number: 'I', range: 'Chapters 1–5', title: 'Foundations', subtitle: 'From industrial software to the IoT platform base', description: 'Architecture, sensing, communication, and platform data processing: how physical signals become reliable data.', link: '/en/foundations/', action: 'Enter Part I'},
      {number: 'II', range: 'Chapters 6–9', title: 'Technology', subtitle: 'Cloud-native and AI-agent capabilities', description: 'Microservices, containers, Agent Runtime, security, and standards: how intelligence enters the platform without bypassing its boundaries.', link: '/en/technical/', action: 'Enter Part II'},
      {number: 'III', range: 'Chapters 10–14', title: 'Applications', subtitle: 'Multi-scenario practice and trusted collaboration', description: 'Industry, cities, agriculture, trusted data, and the IoT DC3 project: how the same base is tested against different constraints.', link: '/en/applications/', action: 'Enter Part III'}
    ]
  },
  outcomes: {
    kicker: 'What you should take away',
    title: 'Not a product manual—a reusable way to reason about systems',
    description: 'IoT DC3 is the open-source engineering reference that runs through parts of the book. The methods, boundaries, and trade-offs are the subject.',
    items: [
      {label: 'Architecture', title: 'Draw the full data loop', description: 'Explain the path from sensing and protocol access to storage, reasoning, command execution, and feedback.'},
      {label: 'Trade-offs', title: 'Choose with conditions attached', description: 'Compare protocols, cloud-edge boundaries, data paths, and security controls together with their costs and failure modes.'},
      {label: 'Practice', title: 'Design a bounded agent system', description: 'Define tool contracts, permissions, policies, confirmation, recovery, and audit before an agent can affect a device.'}
    ]
  },
  clarity: {
    kicker: 'Three boundaries kept explicit',
    title: 'What this book does not claim',
    items: [
      {false: 'MCP replaces device protocols', true: 'MCP connects AI applications to tools and context; MQTT, CoAP, Modbus, and other protocols still connect devices.'},
      {false: 'A model directly controls equipment', true: 'High-risk writes require authorization, validation, policy, audit, and, where necessary, human confirmation.'},
      {false: 'IoT DC3 is the only answer', true: 'It is a concrete engineering reference used to make general architecture patterns and trade-offs inspectable.'}
    ]
  },
  cta: {
    kicker: 'Start with the real problem',
    title: 'Follow one signal from the field to a governed action',
    description: 'Begin with Chapter 1 to follow the full argument, or use the table of contents to enter at the layer closest to your current problem.',
    primary: 'Start Chapter 1',
    primaryLink: '/en/foundations/chapter-1/',
    secondary: 'Browse the contents',
    secondaryLink: '/en/preface/contents',
    guide: 'Not sure where to start? Read the guide first',
    guideLink: '/en/preface/guide'
  }
} : {
  premise: {
    kicker: '全书要回答的问题',
    title: '模型会推理之后，如何安全地触碰真实世界？',
    description: '在工业系统里，答案不能直接变成动作。现场首先要可感知，信号要成为可信上下文，每一次写操作还必须穿过清晰的执行边界。',
    items: [
      {index: '01', eyebrow: '看见', title: '让物理世界可被理解', description: '传感器、协议、驱动、位号值与物模型，把碎片化的现场信号变成稳定的平台数据。'},
      {index: '02', eyebrow: '推理', title: '让数据成为决策上下文', description: '数据处理、规则、RAG、Tool 与 MCP，为智能体理解任务和形成决策提供可用上下文。'},
      {index: '03', eyebrow: '行动', title: '先治理，再执行', description: '身份、鉴权、参数校验、策略、确认、恢复与审计，位于模型意图与物理指令之间。'}
    ],
    boundary: 'LLM 可以理解意图、归纳信息并编排受控工具；实时控制、安全联锁和故障保护，仍应由 PLC、边缘控制器等确定性系统承担。'
  },
  thesis: {
    kicker: '全书主线',
    title: '智能体出现之后，平台没有消失，而是成为它的地基',
    description: '全书不是把工业软件、物联网和 AI 拼成三个专题，而是沿一条逐层累积的工程路径展开。',
    stages: [
      {number: '01', tag: '问题起点', title: '工业软件的能力边界', description: 'SCADA、DCS、MES 与 PLC 解决局部、确定性的关键问题，但数据孤岛和封闭能力边界限制了更大范围的协作。'},
      {number: '02', tag: '平台底座', title: '统一物联网数据与能力', description: '多协议接入、物模型、云边协同与平台数据处理，形成可复用的数字底座。'},
      {number: '03', tag: '决策层', title: '受治理的 Agent Runtime', description: 'Spring AI、RAG、Tool、MCP、状态、Workflow 与审计，把概率性推理收进明确的工程边界。'},
      {number: '04', tag: '演进结果', title: '有边界的自治', description: '系统能够感知、推理、执行、验证与恢复，但不会把模型误当作 PLC 或安全系统。'}
    ],
    formula: ['可信数据', '受治理工具', '确定性执行', '可追溯反馈']
  },
  journey: {
    kicker: '主线的一次具体走查',
    title: '一次振动越限，走完整条链路',
    description: '把全书的机制放进同一次真实事件：从冷却泵的振动位号值上行，到一次经确认的写操作。各步机制分别在第 4–5、7、8 与 14 章展开。',
    steps: [
      {number: '01', title: '上行入库', description: '驱动把振动位号值经 MQTT 上报，带单位与时间戳落入时序库。', ref: '第 4–5 章'},
      {number: '02', title: '越限告警', description: '规则引擎按阈值把异常从海量位号中挑出来，先由确定性逻辑兜底。', ref: '第 5 章'},
      {number: '03', title: '汇总证据', description: '智能体经授权工具读取趋势、负载与维修记录，给出轴承磨损前兆的判断和依据。', ref: '第 7 章'},
      {number: '04', title: '待确认动作', description: '写操作不直接下发：生成待确认 Action，先过校验、权限与风险策略。', ref: '第 7–8 章'},
      {number: '05', title: '确认与回执', description: '人工确认后由确定性链路执行，回执与审计留痕可回查。', ref: '第 8、14 章'}
    ],
    note: '每一步都有明确的责任人：数据归驱动，告警归规则，判断归模型，动作归流程，执行归确定性链路。'
  },
  parts: {
    kicker: '三篇 · 十四章',
    title: '沿着同一条闭环，逐层建立能力',
    description: '每一篇都继承前一篇建立的约束。叙事走到 AI 时，工程底座并没有被丢下。',
    items: [
      {number: '01', range: '第 1–5 章', title: '基础篇', subtitle: '从工业软件到物联网平台底座', description: '体系架构、感知、通信与平台数据处理：物理信号如何成为可靠数据。', link: '/foundations/', action: '进入基础篇'},
      {number: '02', range: '第 6–9 章', title: '技术篇', subtitle: '云原生与 AI 智能体能力', description: '微服务、容器、Agent Runtime、安全与标准：智能如何进入平台，又不绕过平台边界。', link: '/technical/', action: '进入技术篇'},
      {number: '03', range: '第 10–14 章', title: '应用篇', subtitle: '多场景实践与可信协作', description: '工业、城市、农业、可信数据与 IoT DC3 实战：同一底座如何面对不同约束。', link: '/applications/', action: '进入应用篇'}
    ]
  },
  outcomes: {
    kicker: '读完应当带走什么',
    title: '不是一份产品手册，而是一套可迁移的系统思考方法',
    description: 'IoT DC3 是贯穿部分章节的开源工程参照；真正要讲清的是通用方法、责任边界与工程取舍。',
    items: [
      {label: '架构', title: '画出完整的数据闭环', description: '解释感知、协议接入、存储、推理、指令执行与反馈之间的路径和责任。'},
      {label: '取舍', title: '带着条件做技术选择', description: '把协议、云边边界、数据链路与安全控制的适用条件、代价和失败方式放在一起比较。'},
      {label: '实践', title: '设计有边界的智能体系统', description: '在智能体作用于设备之前，定义工具契约、权限、策略、确认、恢复和审计。'}
    ]
  },
  clarity: {
    kicker: '始终说清的三条边界',
    title: '这本书不做哪些承诺',
    items: [
      {false: 'MCP 替代设备协议', true: 'MCP 连接 AI 应用与工具和上下文；MQTT、CoAP、Modbus 等仍负责设备通信。'},
      {false: '模型直接控制设备', true: '高风险写操作必须经过鉴权、校验、策略、审计，以及必要的人工确认。'},
      {false: 'IoT DC3 是唯一答案', true: '它是用于检验通用架构模式与工程取舍的具体开源参照。'}
    ]
  },
  cta: {
    kicker: '从真实问题开始',
    title: '沿一条现场信号，走到一次受治理的行动',
    description: '从第 1 章开始，可以完整跟随全书论证；也可以打开目录，从与你当前问题最接近的一层进入。',
    primary: '从第 1 章开始',
    primaryLink: '/foundations/chapter-1/',
    secondary: '浏览全书目录',
    secondaryLink: '/preface/contents',
    guide: '不确定从哪开始？先看导读',
    guideLink: '/preface/guide'
  }
})
</script>

<template>
  <main class="book-home-story">
    <section class="book-home-section book-home-premise">
      <div class="book-home-container">
        <header class="book-home-heading">
          <span class="book-home-kicker">{{ copy.premise.kicker }}</span>
          <h2>{{ copy.premise.title }}</h2>
          <p>{{ copy.premise.description }}</p>
        </header>

        <div class="book-home-premise-grid">
          <article v-for="item in copy.premise.items" :key="item.index" class="book-home-card book-home-premise-card">
            <div class="book-home-card-meta">
              <span>{{ item.index }}</span>
              <strong>{{ item.eyebrow }}</strong>
            </div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.description }}</p>
          </article>
        </div>

        <p class="book-home-boundary">{{ copy.premise.boundary }}</p>
      </div>
    </section>

    <section class="book-home-section book-home-thesis">
      <div class="book-home-container">
        <header class="book-home-heading">
          <span class="book-home-kicker">{{ copy.thesis.kicker }}</span>
          <h2>{{ copy.thesis.title }}</h2>
          <p>{{ copy.thesis.description }}</p>
        </header>

        <ol class="book-home-stages">
          <li v-for="stage in copy.thesis.stages" :key="stage.number" class="book-home-stage">
            <div class="book-home-stage-index">
              <span>{{ stage.number }}</span>
              <small>{{ stage.tag }}</small>
            </div>
            <div>
              <h3>{{ stage.title }}</h3>
              <p>{{ stage.description }}</p>
            </div>
          </li>
        </ol>

        <div class="book-home-formula" :aria-label="copy.thesis.formula.join(' → ')">
          <template v-for="(item, index) in copy.thesis.formula" :key="item">
            <span>{{ item }}</span>
            <b v-if="index < copy.thesis.formula.length - 1" aria-hidden="true">→</b>
          </template>
        </div>
      </div>
    </section>

    <section class="book-home-section book-home-journey">
      <div class="book-home-container">
        <header class="book-home-heading">
          <span class="book-home-kicker">{{ copy.journey.kicker }}</span>
          <h2>{{ copy.journey.title }}</h2>
          <p>{{ copy.journey.description }}</p>
        </header>

        <div class="book-home-card book-home-journey-panel">
          <ol class="book-home-journey-steps">
            <li v-for="step in copy.journey.steps" :key="step.number" class="book-home-journey-step">
              <span class="book-home-journey-node">{{ step.number }}</span>
              <div class="book-home-journey-body">
                <h3>{{ step.title }}</h3>
                <p>{{ step.description }}</p>
                <small>{{ step.ref }}</small>
              </div>
            </li>
          </ol>
          <p class="book-home-journey-note">{{ copy.journey.note }}</p>
        </div>
      </div>
    </section>

    <section class="book-home-section book-home-parts">
      <div class="book-home-container">
        <header class="book-home-heading">
          <span class="book-home-kicker">{{ copy.parts.kicker }}</span>
          <h2>{{ copy.parts.title }}</h2>
          <p>{{ copy.parts.description }}</p>
        </header>

        <div class="book-home-parts-grid">
          <a v-for="part in copy.parts.items" :key="part.number" :href="part.link" class="book-home-card book-home-part-card">
            <div class="book-home-part-top">
              <span class="book-home-part-number">{{ part.number }}</span>
              <span class="book-home-part-range">{{ part.range }}</span>
            </div>
            <h3>{{ part.title }}</h3>
            <strong>{{ part.subtitle }}</strong>
            <p>{{ part.description }}</p>
            <span class="book-home-part-action">{{ part.action }} <i aria-hidden="true">→</i></span>
          </a>
        </div>
      </div>
    </section>

    <section class="book-home-section book-home-outcomes">
      <div class="book-home-container">
        <header class="book-home-heading">
          <span class="book-home-kicker">{{ copy.outcomes.kicker }}</span>
          <h2>{{ copy.outcomes.title }}</h2>
          <p>{{ copy.outcomes.description }}</p>
        </header>

        <div class="book-home-outcomes-grid">
          <article v-for="item in copy.outcomes.items" :key="item.label">
            <span>{{ item.label }}</span>
            <h3>{{ item.title }}</h3>
            <p>{{ item.description }}</p>
          </article>
        </div>
      </div>
    </section>

    <section class="book-home-section book-home-clarity">
      <div class="book-home-container book-home-clarity-inner">
        <header class="book-home-heading">
          <span class="book-home-kicker">{{ copy.clarity.kicker }}</span>
          <h2>{{ copy.clarity.title }}</h2>
        </header>

        <div class="book-home-clarity-list">
          <article v-for="item in copy.clarity.items" :key="item.false">
            <div class="book-home-clarity-no"><span aria-hidden="true">×</span>{{ item.false }}</div>
            <div class="book-home-clarity-yes"><span aria-hidden="true">→</span>{{ item.true }}</div>
          </article>
        </div>
      </div>
    </section>

    <section class="book-home-cta">
      <div class="book-home-container">
        <span class="book-home-kicker">{{ copy.cta.kicker }}</span>
        <h2>{{ copy.cta.title }}</h2>
        <p>{{ copy.cta.description }}</p>
        <div class="book-home-cta-actions">
          <a class="book-home-button book-home-button-primary" :href="copy.cta.primaryLink">{{ copy.cta.primary }} <span aria-hidden="true">→</span></a>
          <a class="book-home-button book-home-button-secondary" :href="copy.cta.secondaryLink">{{ copy.cta.secondary }}</a>
        </div>
        <a class="book-home-cta-guide" :href="copy.cta.guideLink">{{ copy.cta.guide }} <i aria-hidden="true">→</i></a>
      </div>
    </section>
  </main>
</template>

<style scoped>
.book-home-story {
  --book-home-border: color-mix(in srgb, var(--vp-c-brand-1) 16%, var(--vp-c-divider));
  --book-home-glass: color-mix(in srgb, var(--vp-c-bg) 82%, transparent);
  width: 100%;
  margin: 0;
  color: var(--vp-c-text-1);
}

/* VitePress 默认给首页 Markdown 内容保留文档页宽度与左右内边距。
   本页的各节自己管理内容宽度，因此直接铺满实际可用宽度，避免用 100vw
   或负边距扩展时把 Windows 纵向滚动条宽度计入，产生横向滚动。 */
:global(.VPHome > .vp-doc.container) {
  max-width: none;
  padding-right: 0;
  padding-left: 0;
}

.book-home-container {
  width: min(1180px, calc(100% - 64px));
  margin: 0 auto;
}

.book-home-section {
  position: relative;
  padding: 118px 0;
}

.book-home-heading {
  max-width: 820px;
  margin: 0 auto;
  text-align: center;
}

.book-home-kicker {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 6px 12px;
  border: 1px solid color-mix(in srgb, var(--vp-c-brand-1) 20%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--vp-c-brand-soft) 54%, transparent);
  color: var(--vp-c-brand-1);
  font-size: 12px;
  font-weight: 720;
  line-height: 1;
  letter-spacing: .13em;
}

.book-home-heading h2,
.book-home-cta h2 {
  margin: 18px auto 0;
  border: 0;
  color: var(--vp-c-text-1);
  font-size: clamp(34px, 4.3vw, 56px);
  font-weight: 770;
  line-height: 1.12;
  letter-spacing: -.045em;
}

.book-home-heading > p,
.book-home-cta > .book-home-container > p {
  max-width: 720px;
  margin: 18px auto 0;
  color: var(--vp-c-text-2);
  font-size: 17px;
  line-height: 1.8;
}

.book-home-premise {
  padding-top: 102px;
}

.book-home-premise-grid,
.book-home-parts-grid,
.book-home-outcomes-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-top: 56px;
}

.book-home-card {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--book-home-border);
  border-radius: 22px;
  background:
    radial-gradient(circle at 100% 0%, rgba(18, 150, 219, .1), transparent 44%),
    linear-gradient(150deg, rgba(255, 255, 255, .5), var(--book-home-glass));
  box-shadow: 0 16px 42px rgba(16, 96, 161, .07), inset 0 1px 0 rgba(255, 255, 255, .72);
  text-align: left;
  transition: transform .28s ease, border-color .28s ease, box-shadow .28s ease;
}

.book-home-card::before {
  content: '';
  position: absolute;
  top: 0;
  right: 24px;
  left: 24px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--vp-c-brand-1), transparent);
}

.book-home-card:hover,
.book-home-stage:hover {
  border-color: color-mix(in srgb, var(--vp-c-brand-1) 42%, transparent);
  box-shadow: 0 24px 52px rgba(16, 96, 161, .13), inset 0 1px 0 rgba(255, 255, 255, .82);
  transform: translateY(-5px);
}

.book-home-premise-card {
  min-height: 270px;
  padding: 28px;
}

.book-home-card-meta,
.book-home-part-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.book-home-card-meta span,
.book-home-part-range {
  color: var(--vp-c-text-3);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: .08em;
  font-family: var(--vp-font-family-mono);
}

.book-home-card-meta strong {
  color: var(--vp-c-brand-1);
  font-size: 13px;
  letter-spacing: .08em;
}

.book-home-premise-card h3 {
  margin: 58px 0 0;
  font-size: 22px;
  line-height: 1.3;
}

.book-home-premise-card p,
.book-home-part-card p,
.book-home-outcomes-grid p,
.book-home-stage p {
  margin: 13px 0 0;
  color: var(--vp-c-text-2);
  font-size: 14.5px;
  line-height: 1.75;
  text-align: left;
}

.book-home-boundary {
  max-width: 980px;
  margin: 48px auto 0;
  padding: 22px 28px;
  border: 1px solid color-mix(in srgb, var(--vp-c-brand-1) 22%, transparent);
  border-radius: 18px;
  background: color-mix(in srgb, var(--vp-c-brand-soft) 48%, transparent);
  color: var(--vp-c-text-1);
  font-size: 16px;
  font-weight: 620;
  line-height: 1.75;
  text-align: center;
}

.book-home-thesis,
.book-home-clarity {
  border-top: 1px solid color-mix(in srgb, var(--vp-c-brand-1) 9%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--vp-c-brand-1) 9%, transparent);
  background:
    radial-gradient(circle at 8% 18%, rgba(18, 150, 219, .07), transparent 28%),
    radial-gradient(circle at 92% 82%, rgba(91, 116, 235, .07), transparent 28%),
    color-mix(in srgb, var(--vp-c-bg-alt) 62%, transparent);
}

.book-home-stages {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  /* 34px 的连接节点完整落在 44px 间隙内，两侧各保留 5px，不再压住卡片描边。 */
  gap: 44px;
  max-width: 1180px;
  margin: 60px auto 0;
  padding: 0;
  list-style: none;
}

.book-home-stage {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 286px;
  flex-direction: column;
  align-items: flex-start;
  margin: 0;
  padding: 28px 25px 26px;
  border: 1px solid var(--book-home-border);
  border-radius: 20px;
  background: color-mix(in srgb, var(--vp-c-bg) 78%, transparent);
  box-shadow: 0 12px 32px rgba(16, 96, 161, .05);
  text-align: left;
  overflow: visible;
  transition: transform .28s ease, border-color .28s ease, box-shadow .28s ease;
}

.book-home-stage::before {
  content: '';
  position: absolute;
  top: -1px;
  right: 22px;
  left: 22px;
  height: 3px;
  border-radius: 0 0 999px 999px;
  background: linear-gradient(90deg, #29c5df, #1296db 52%, #5b74eb);
  opacity: .78;
}

.book-home-stage:not(:last-child)::after {
  content: '→';
  position: absolute;
  z-index: 2;
  top: 50%;
  right: -39px;
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid var(--book-home-border);
  border-radius: 50%;
  background: var(--vp-c-bg-alt);
  box-shadow: 0 8px 18px rgba(16, 96, 161, .1);
  color: var(--vp-c-brand-1);
  font-size: 17px;
  font-weight: 750;
  transform: translateY(-50%);
}

.book-home-stage-index {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.book-home-stage-index span {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, .42);
  border-radius: 15px;
  background: linear-gradient(145deg, #07549a, #1296db 52%, #5558c9);
  box-shadow: 0 10px 24px rgba(13, 114, 180, .2), inset 0 1px 0 rgba(255, 255, 255, .3);
  color: #fff;
  font-size: 14px;
  font-weight: 760;
  font-family: var(--vp-font-family-mono);
}

.book-home-stage-index small {
  padding: 6px 9px;
  border: 1px solid color-mix(in srgb, var(--vp-c-brand-1) 16%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--vp-c-brand-soft) 46%, transparent);
  color: var(--vp-c-text-3);
  font-size: 10px;
  font-weight: 650;
  letter-spacing: .06em;
  white-space: nowrap;
}

.book-home-stage h3 {
  margin: 34px 0 0;
  font-size: 21px;
  line-height: 1.36;
}

.book-home-formula {
  display: flex;
  gap: 14px;
  align-items: center;
  justify-content: center;
  margin: 48px auto 0;
  padding: 20px 24px;
  border: 1px solid var(--book-home-border);
  border-radius: 999px;
  background: color-mix(in srgb, var(--vp-c-bg) 74%, transparent);
  box-shadow: inset 0 1px 0 color-mix(in srgb, #fff 54%, transparent);
}

.book-home-formula span {
  color: var(--vp-c-text-1);
  font-size: 15px;
  font-weight: 680;
  white-space: nowrap;
}

.book-home-formula b {
  color: var(--vp-c-brand-1);
  font-weight: 720;
}

.book-home-journey-panel {
  margin-top: 56px;
  padding: 40px 36px 30px;
}

.book-home-journey-steps {
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 18px;
  margin: 0;
  padding: 0;
  list-style: none;
}

/* 连接线只贯穿首尾节点圆心：五等分栏的圆心分别落在 10% 与 90% 处 */
.book-home-journey-steps::before {
  content: '';
  position: absolute;
  z-index: 0;
  top: 17px;
  left: 10%;
  right: 10%;
  height: 2px;
  background: linear-gradient(90deg, #29c5df, #1296db 52%, #5b74eb);
  opacity: .5;
}

.book-home-journey-step {
  position: relative;
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  margin: 0;
  text-align: center;
}

.book-home-journey-node {
  position: relative;
  z-index: 1;
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, .42);
  border-radius: 50%;
  background: linear-gradient(145deg, #07549a, #1296db 52%, #5558c9);
  box-shadow: 0 8px 20px rgba(13, 114, 180, .22), inset 0 1px 0 rgba(255, 255, 255, .3);
  color: #fff;
  font-size: 12px;
  font-weight: 760;
  font-family: var(--vp-font-family-mono);
}

.book-home-journey-body h3 {
  margin: 16px 0 0;
  font-size: 16.5px;
  line-height: 1.4;
}

.book-home-journey-body p {
  margin: 9px 0 0;
  color: var(--vp-c-text-2);
  font-size: 13.5px;
  line-height: 1.7;
}

.book-home-journey-body small {
  display: inline-block;
  margin-top: 12px;
  padding: 4px 10px;
  border: 1px solid color-mix(in srgb, var(--vp-c-brand-1) 16%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--vp-c-brand-soft) 46%, transparent);
  color: var(--vp-c-text-3);
  font-size: 10.5px;
  font-weight: 650;
  letter-spacing: .06em;
  font-family: var(--vp-font-family-mono);
  white-space: nowrap;
}

.book-home-journey-note {
  margin: 26px auto 0;
  padding-top: 22px;
  border-top: 1px dashed var(--book-home-border);
  color: var(--vp-c-text-2);
  font-size: 14px;
  line-height: 1.75;
  text-align: center;
}

.book-home-part-card {
  display: flex;
  flex-direction: column;
  min-height: 390px;
  padding: 30px;
  color: inherit;
  text-decoration: none;
}

.book-home-part-card:hover {
  color: inherit;
  text-decoration: none;
}

.book-home-part-number {
  background: linear-gradient(112deg, #07549a, #119bd6 48%, #5558c9);
  background-clip: text;
  color: transparent;
  font-size: 46px;
  font-weight: 800;
  line-height: 1;
}

.book-home-part-card h3 {
  margin: 48px 0 0;
  font-size: 25px;
}

.book-home-part-card > strong {
  margin-top: 8px;
  color: var(--vp-c-brand-1);
  font-size: 14px;
  line-height: 1.55;
}

.book-home-part-action {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  margin-top: auto;
  padding-top: 26px;
  color: var(--vp-c-brand-1);
  font-size: 14px;
  font-weight: 680;
}

.book-home-part-action i {
  font-style: normal;
  transition: transform .22s ease;
}

.book-home-part-card:hover .book-home-part-action i {
  transform: translateX(4px);
}

.book-home-outcomes {
  padding-top: 104px;
}

.book-home-outcomes-grid article {
  padding: 8px 30px 10px;
  border-left: 1px solid var(--book-home-border);
  text-align: left;
}

.book-home-outcomes-grid article:first-child {
  border-left: 0;
}

.book-home-outcomes-grid span {
  color: var(--vp-c-brand-1);
  font-size: 12px;
  font-weight: 720;
  letter-spacing: .14em;
}

.book-home-outcomes-grid h3 {
  margin: 32px 0 0;
  font-size: 22px;
  line-height: 1.35;
}

.book-home-clarity-inner {
  max-width: 1040px;
}

.book-home-clarity-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 56px;
}

.book-home-clarity-list article {
  display: grid;
  grid-template-columns: minmax(220px, .72fr) minmax(0, 1.7fr);
  overflow: hidden;
  border: 1px solid var(--book-home-border);
  border-radius: 18px;
  background: color-mix(in srgb, var(--vp-c-bg) 78%, transparent);
}

.book-home-clarity-no,
.book-home-clarity-yes {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 22px 24px;
  font-size: 14.5px;
  line-height: 1.65;
}

.book-home-clarity-no {
  color: var(--vp-c-text-2);
  text-decoration: line-through;
  text-decoration-color: color-mix(in srgb, var(--vp-c-danger-1) 60%, transparent);
}

.book-home-clarity-yes {
  border-left: 1px solid var(--book-home-border);
  color: var(--vp-c-text-1);
  font-weight: 610;
}

.book-home-clarity-no span {
  color: var(--vp-c-danger-1);
  font-size: 20px;
  text-decoration: none;
}

.book-home-clarity-yes span {
  color: var(--vp-c-brand-1);
  font-size: 18px;
}

.book-home-cta {
  position: relative;
  padding: 126px 0 136px;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 122%, rgba(41, 197, 223, .24), transparent 54%),
    radial-gradient(circle at 8% 10%, rgba(18, 150, 219, .1), transparent 31%),
    radial-gradient(circle at 92% 14%, rgba(91, 116, 235, .12), transparent 31%);
  text-align: center;
}

.book-home-cta h2 {
  max-width: 880px;
}

.book-home-cta-actions {
  display: flex;
  gap: 14px;
  justify-content: center;
  margin-top: 34px;
}

.book-home-button {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: 12px 25px;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 680;
  text-decoration: none;
  transition: transform .22s ease, box-shadow .22s ease;
}

.book-home-button:hover {
  text-decoration: none;
  transform: translateY(-2px);
}

.book-home-button-primary {
  border: 1px solid rgba(255, 255, 255, .2);
  background: linear-gradient(150deg, #07549a, #0d8fd0 52%, #4f52bf 120%);
  box-shadow: 0 16px 38px rgba(13, 114, 180, .24);
  color: #fff;
}

.book-home-button-primary:hover {
  box-shadow: 0 20px 44px rgba(13, 114, 180, .32);
  color: #fff;
}

.book-home-button-secondary {
  border: 1px solid var(--book-home-border);
  background: var(--book-home-glass);
  color: var(--vp-c-text-1);
}

.book-home-button-secondary:hover {
  color: var(--vp-c-text-1);
}

.book-home-cta-guide {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  margin-top: 20px;
  color: var(--vp-c-text-2);
  font-size: 14px;
  text-decoration: none;
  transition: color .22s ease;
}

.book-home-cta-guide:hover {
  color: var(--vp-c-brand-1);
}

.book-home-cta-guide i {
  font-style: normal;
}

/* 暗色主题：注意 scoped 样式里 :global(.dark) X 的混写形式会被编译器整条丢弃，
   必须写成普通祖先选择器 .dark X（编译为 .dark X[data-v-…]）。 */
.dark .book-home-story {
  --book-home-border: color-mix(in srgb, var(--vp-c-brand-1) 28%, rgba(148, 184, 220, .14));
}

.dark .book-home-card,
.dark .book-home-stage {
  border-color: var(--book-home-border);
  background:
    radial-gradient(circle at 100% 0%, rgba(41, 197, 223, .12), transparent 44%),
    linear-gradient(150deg, rgba(35, 56, 82, .68), rgba(20, 33, 50, .84) 52%, rgba(34, 42, 84, .6));
  box-shadow: 0 18px 40px rgba(0, 0, 0, .34), inset 0 1px 0 rgba(232, 251, 255, .1);
}

/* 暗色悬停：与上面的表面规则同特异性，靠 :hover 提高一级压过它，
   否则基础规则会把悬停的描边变亮与阴影加深全部压平（transform 不受影响） */
.dark .book-home-card:hover,
.dark .book-home-stage:hover {
  border-color: color-mix(in srgb, var(--vp-c-brand-1) 55%, transparent);
  box-shadow: 0 26px 56px rgba(0, 0, 0, .5), inset 0 1px 0 rgba(232, 251, 255, .16);
}

.dark .book-home-part-number {
  background: linear-gradient(112deg, #8edcff, #d3fbff 48%, #a6a9ff);
  background-clip: text;
}

/* 暗色下 tinted 区块反转为略亮于页面底（bg-alt 在暗色下比 bg 更暗，原写法会形成"暗带"） */
.dark .book-home-thesis,
.dark .book-home-clarity {
  border-top-color: color-mix(in srgb, var(--vp-c-brand-1) 15%, transparent);
  border-bottom-color: color-mix(in srgb, var(--vp-c-brand-1) 15%, transparent);
  background:
    radial-gradient(circle at 8% 18%, rgba(41, 197, 223, .05), transparent 28%),
    radial-gradient(circle at 92% 82%, rgba(91, 116, 235, .07), transparent 28%),
    linear-gradient(180deg, rgba(26, 42, 62, .42), rgba(17, 28, 43, .55));
}

.dark .book-home-formula {
  background: color-mix(in srgb, var(--vp-c-bg-elv) 74%, transparent);
  box-shadow: inset 0 1px 0 rgba(232, 251, 255, .09);
}

@media (max-width: 1100px) {
  .book-home-stages {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 22px;
  }

  .book-home-stage {
    min-height: 236px;
  }

  .book-home-stage:not(:last-child)::after {
    display: none;
  }

  .book-home-journey-steps {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  /* 窄屏改为左侧竖向导轨：导轨对准 36px 节点的圆心（x=18），节点列固定不缩放 */
  .book-home-journey-steps::before {
    top: 20px;
    bottom: 20px;
    left: 17px;
    right: auto;
    width: 2px;
    height: auto;
    background: linear-gradient(180deg, #29c5df, #1296db 52%, #5b74eb);
  }

  .book-home-journey-step {
    display: grid;
    grid-template-columns: 36px minmax(0, 1fr);
    gap: 16px;
    align-items: start;
    text-align: left;
  }

  .book-home-journey-body h3 {
    margin-top: 5px;
  }

  .book-home-journey-body p {
    margin-top: 7px;
  }
}

@media (max-width: 900px) {
  .book-home-container {
    width: min(100% - 48px, 1180px);
  }

  .book-home-section {
    padding: 92px 0;
  }

  .book-home-premise-grid,
  .book-home-parts-grid {
    grid-template-columns: 1fr;
  }

  .book-home-premise-card {
    min-height: 0;
  }

  .book-home-premise-card h3 {
    margin-top: 40px;
  }

  .book-home-part-card {
    min-height: 330px;
  }

  .book-home-outcomes-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }

  .book-home-outcomes-grid article,
  .book-home-outcomes-grid article:first-child {
    padding: 30px 8px;
    border-top: 1px solid var(--book-home-border);
    border-left: 0;
  }

  .book-home-outcomes-grid article:first-child {
    border-top: 0;
  }
}

@media (max-width: 640px) {
  .book-home-container {
    width: min(100% - 36px, 1180px);
  }

  .book-home-section {
    padding: 78px 0;
  }

  .book-home-heading h2,
  .book-home-cta h2 {
    font-size: clamp(30px, 9.4vw, 42px);
  }

  .book-home-heading > p,
  .book-home-cta > .book-home-container > p {
    font-size: 15.5px;
  }

  .book-home-premise-grid,
  .book-home-parts-grid,
  .book-home-outcomes-grid {
    margin-top: 42px;
  }

  .book-home-boundary {
    padding: 20px;
    text-align: left;
  }

  .book-home-stages {
    grid-template-columns: 1fr;
    gap: 44px;
  }

  .book-home-stage {
    min-height: 0;
    padding: 24px 22px;
  }

  .book-home-stage:not(:last-child)::after {
    content: '↓';
    top: auto;
    right: auto;
    bottom: -37px;
    left: 50%;
    display: grid;
    width: 30px;
    height: 30px;
    font-size: 14px;
    transform: translateX(-50%);
  }

  .book-home-stage h3 {
    margin-top: 24px;
  }

  .book-home-stage-index span {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    font-size: 12px;
  }

  .book-home-formula {
    flex-direction: column;
    border-radius: 20px;
  }

  .book-home-formula b {
    transform: rotate(90deg);
  }

  .book-home-part-card {
    min-height: 0;
    padding: 26px;
  }

  .book-home-clarity-list article {
    grid-template-columns: 1fr;
  }

  .book-home-clarity-yes {
    border-top: 1px solid var(--book-home-border);
    border-left: 0;
  }

  .book-home-cta {
    padding: 94px 0 104px;
  }

  .book-home-cta-actions {
    flex-direction: column;
    align-items: center;
  }

  .book-home-button {
    width: min(320px, 100%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .book-home-card,
  .book-home-stage,
  .book-home-button,
  .book-home-part-action i {
    transition: none;
  }

  .book-home-card:hover,
  .book-home-stage:hover,
  .book-home-button:hover {
    transform: none;
  }
}
</style>
