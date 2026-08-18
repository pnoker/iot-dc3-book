# Translation Contract (mandatory for every section)

You are translating ONE section file of a published technical book
《从工业软件到 AI 智能体》 ("From Industrial Software to AI Agents") from Chinese
to English. The book teaches IoT platform engineering, cloud-native architecture,
and AI agents in industrial settings. Translation quality bar: the pair
`book/manuscript/zh/chapter-01/1.1.md` (source) ↔ `book/manuscript/en/chapter-01/1.1.md`
(translation). READ BOTH before you start.

## Output file

`book/manuscript/en/chapter-XX/X.Y.md` — same filename as the source
`book/manuscript/zh/chapter-XX/X.Y.md`. Write it only; touch nothing else.

## Structure fidelity (absolute rules)

1. Frontmatter: `section: "X.Y <English H2 title>"` (translate the title).
2. `## X.Y English Title` — keep the numeric stem exact. H3/H4 headings keep
   their `X.Y.Z` numbering, translated.
3. **Figure anchors `@[fig-XX-YY]` are language-neutral placeholders. Copy them
   verbatim, on their own line, at the exact position between the same two
   paragraphs as in the source. Do not translate, move, add, or drop them.**
4. Fenced code blocks (``` … ```): code logic, identifiers, API calls and config
   keys are copied **byte-identical** from the source — never translate code.
   Human-readable content inside blocks IS translated to English: comments,
   prompt-template strings, sample inputs/outputs, JSON `title`/`description`
   fields, pseudocode step lines, and `□` checklist entries. Translating these
   must not change the code's semantics or line structure.
5. Inline code spans (`…`): keep as-is.
6. Tables: same shape (rows/columns), translate header and body cells; keep all
   numbers, units, and product names exact.
7. Lists: mirror item count and order. Bold/italic emphasis on the same words.
8. One source paragraph → one target paragraph. Do not merge, split, add, or
   delete paragraphs. No new headings, no notes from you.
9. Cross-references: 第 N 章 → Chapter N; 第 N.M 节 / N.M 节 → Section N.M;
   图 N-M → Figure N-M; 表 N-M → Table N-M; 下文/后文 references phrased naturally.

## Language style

- Professional technical-publishing register: precise, restrained, engineering-
  focused. No marketing words (revolutionize, unleash, seamless, effortless).
- Mirror the argument order within each paragraph; translate, don't rewrite.
- The source introduces terms as 中文名（English Name, ABBR）. In English, use the
  full name + abbreviation at first occurrence in the chapter (e.g. "SCADA
  (Supervisory Control and Data Acquisition)"), then the abbreviation alone.
- Units and measurements preserved exactly (0.63 MPa, 85 °C, I²C, ms-level).
- English punctuation. Em dash " — " for 破折号; straight double quotes.
- Chinese idioms/metaphors: keep the image if it reads naturally; otherwise use
  the plainest accurate English (the 1.1 exemplar shows the register).

## Glossary (use EXACTLY these; do not invent variants)

物联网=IoT / Internet of Things; 工业物联网=industrial IoT (IIoT);
感知层=sensing layer; 网络层=network layer; 平台层=platform layer;
应用层=application layer; 智能层=intelligence layer; 五层架构=five-layer architecture;
物模型=thing model; 位号=point; 位号值=point value; 测点=point;
设备影子=device shadow; 驱动=driver; 驱动框架=driver framework; 网关=gateway;
边缘节点=edge node; 边缘计算=edge computing; 边云协同=edge-cloud collaboration;
云原生=cloud-native; 微服务=microservice; 容器化=containerization;
多租户=multi-tenancy; 租户=tenant; 数据归一=unified data;
能力开放=open capabilities; 闭环自动化=closed-loop automation; 数据闭环=data loop;
智能体=AI agent (agent after first use); 大语言模型=large language model (LLM);
检索增强生成=retrieval-augmented generation (RAG); 工具调用=tool calling;
模型上下文协议=Model Context Protocol (MCP); 智能决策中枢=Agentic Center;
有界自治=bounded autonomy; 预测性维护=predictive maintenance;
数字孪生=digital twin; 规则引擎=rule engine; 时序数据库=time-series database;
消息队列=message queue; 指令=command; 事件=event; 属性=attribute; 告警=alarm;
鉴权=authorization; 审计=audit; 安全联锁=safety interlock; 急停=e-stop;
可编程逻辑控制器=PLC; 监控与数据采集=SCADA; 制造执行系统=manufacturing execution system (MES);
企业资源计划=ERP; 人机界面=HMI; 分布式控制系统=DCS;
低功耗广域网=LPWAN; 车联网=connected vehicles (V2X where protocol-level);
智慧城市=smart city; 精准农业=precision agriculture; 联邦学习=federated learning;
区块链=blockchain; 分布式身份=decentralized identity (DID);
隐私计算=privacy-preserving computation; 供应链溯源=supply-chain traceability;
状态机=state machine; 工作流=workflow; 降级=degrade/fallback;
统一接入层=unified access layer; 协议碎片化=protocol fragmentation;
提示注入=prompt injection; 越权=privilege escalation; 多协议=multi-protocol;
开源=open-source; 工业软件=industrial software; 架构跃迁=architectural leap;
裂缝=crack; 结构性局限/张力=structural limits/tension.
Terms not listed: prefer the appendix A equivalent in the source's own
中文名（English, ABBR）parenthesis; keep one translation consistently.

## Self-check (run after writing; fix until it passes)

```bash
cd /Users/pnoker/Code/pnoker/IoTDC3/github/iot-dc3-book && python3 - <<'EOF'
import re
src = open('book/manuscript/zh/chapter-XX/X.Y.md', encoding='utf-8').read()
dst = open('book/manuscript/en/chapter-XX/X.Y.md', encoding='utf-8').read()
a1 = re.findall(r'@\[(fig-\d+-\d+)\]', src); a2 = re.findall(r'@\[(fig-\d+-\d+)\]', dst)
assert a1 == a2, f'anchors differ: {a1} vs {a2}'
def noc(t): return re.sub(r'```.*?```', '', t, flags=re.DOTALL)
cjk = re.findall(r'[\u4e00-\u9fff]', noc(dst))
assert not cjk, f'CJK outside code: {len(cjk)} chars'
for pat, name in [(r'^## (\d+\.\d+)', 'H2'), (r'^### (\d+\.\d+\.\d+)', 'H3')]:
    s, d = re.findall(pat, src, re.M), re.findall(pat, dst, re.M)
    assert s == d, f'{name} numbering: {s} vs {d}'
fs, fd = len(re.findall(r'^```', src, re.M)), len(re.findall(r'^```', dst, re.M))
assert fs == fd, f'fence count {fs} vs {fd}'
ts, td = len(re.findall(r'^\|', src, re.M)), len(re.findall(r'^\|', dst, re.M))
assert ts == td, f'table rows {ts} vs {td}'
words = len(re.findall(r"[A-Za-z0-9'-]+", noc(dst)))
print(f'OK anchors={len(a1)} H2={len(re.findall(chr(94)+chr(35)+chr(35)+chr(32), src, re.M))-1} words={words}')
EOF
```

(Replace chapter-XX/X.Y.md with your assignment.) Final message: exactly one
line — `OK words=<n>` or a precise description of any unresolved issue.
