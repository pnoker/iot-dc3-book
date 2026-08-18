# Appendix

## A. Glossary

| Term | English / Full Name | Description |
|---|---|---|
| AIoT | Artificial Intelligence of Things | Deep fusion of AI and IoT — from passive connectivity to active intelligence |
| MCP | Model Context Protocol | Open standard (Anthropic, 2024) for interaction between AI and external tools and data sources |
| Tool calling | Tool calling | Mechanism by which an LLM invokes external tools (e.g., devices) via function calls |
| RAG | Retrieval-Augmented Generation | Model answers augmented with retrieved knowledge |
| Agent | AI Agent | Intelligent agent that perceives, reasons, plans, and executes multi-step tasks |
| Thing model | Thing Model / Profile | Abstraction of device capabilities (properties/services/events) that hides protocol differences |
| Point value | Point Value | Semantically tagged device data point (device ID + timestamp + unit + value) |
| Agentic Center | Agentic Center | IoT DC3's intelligent decision hub, built on Spring AI |
| LPWAN | Low-Power Wide-Area Network | Low-power wide-area network technologies such as NB-IoT and LoRa |
| RedCap | Reduced Capability | Lightweight 5G (Rel-17) for mid-tier IoT |
| TSFM | Time Series Foundation Model | Time-series foundation models (e.g., TimesFM, Chronos) for zero-shot forecasting |
| Device shadow | Device Shadow | Desired/actual device state maintained by the platform, decoupled from online status |
| Edge-cloud collaboration | Edge-Cloud Collaboration | Tiered collaboration: real-time processing at the edge, deep compute in the cloud |
| RBAC/ABAC | Role/Attribute-Based Access Control | Access control based on roles or attributes |

## B. References

1. 3GPP TS 22.261 / 36.300 / 38.300 — Mobile communications system architecture and service requirements
2. 3GPP TR 38.875 (RedCap) / TR 38.821 (NTN) — Lightweight 5G and non-terrestrial networks
3. CSA, *Matter Specification* — Unified application-layer standard for smart homes
4. OASIS, *MQTT Version 5.0* — Message Queuing Telemetry Transport
5. IETF, *RFC 7252 (CoAP)* / *draft-ietf-oauth-v2-1 (OAuth 2.1 draft)* / *RFC 8628 (device authorization flow)*
6. Anthropic, *Model Context Protocol (MCP) Specification* — Open standard for AI–tool interaction
7. Spring reference documentation — *Spring Boot 4.0 / Spring Cloud 2025.1 / Spring AI 2.0*
8. IoT Analytics, *State of IoT* — Global installed base of IoT devices and industry data
9. LoRa Alliance, *LoRaWAN Specification 1.0.4 / 1.1*
10. IoT DC3 open-source project — https://gitee.com/pnoker/iot-dc3 (running case throughout the book)

## C. Index

**Protocols & communication**: MQTT / CoAP / LwM2M / Modbus / OPC UA / NB-IoT / LoRa(WAN) / 5G (RedCap/NTN) / Wi-Fi / BLE / Zigbee / Matter / Thread / gRPC / REST

**Architecture & platform**: Five-layer architecture / intelligence layer / microservices / Gateway / Auth / Manager / Data / Agentic / thing model / point value / device shadow / time-series database / message queue / rule engine / edge-cloud collaboration

**AI & agents**: Large language model (LLM) / Agent / RAG / Tool calling / MCP / Spring AI / Agentic Center / natural-language operations / anomaly detection / predictive maintenance / TSFM / on-device SLM

**Security**: OAuth 2.1 (IETF draft) / JWT / X.509 certificates / TLS 1.3 / DTLS / RBAC / ABAC / multi-tenancy / prompt injection / PQC (post-quantum cryptography)

**Application scenarios**: Industrial IoT (IIoT) / digital twins / smart cities / connected vehicles (V2X) / precision agriculture / blockchain + IoT / supply-chain traceability
