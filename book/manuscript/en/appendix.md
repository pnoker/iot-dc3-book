# Appendix

## A. Glossary

| Term | English / Full Name | Description |
|---|---|---|
| AIoT | Artificial Intelligence of Things | Deep fusion of AI and IoT — from passive connectivity to active intelligence |
| MCP | Model Context Protocol | Open standard (Anthropic, 2024) for interaction between AI and external tools and data sources; donated in December 2025 to the Agentic AI Foundation under the Linux Foundation |
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
| MQTT | Message Queuing Telemetry Transport | De facto standard messaging protocol for the IoT |
| CoAP | Constrained Application Protocol | Lean web protocol for constrained devices (RFC 7252) |
| LwM2M | Lightweight M2M | Lightweight device-management protocol defined by OMA (over CoAP) |
| OPC UA | OPC Unified Architecture | Industrial interoperability application-layer protocol (IEC 62541) |
| QoS | Quality of Service | Message-delivery semantics: at most once (0) / at least once (1) / exactly once (2) |
| Time-series database | Time Series Database | Storage and aggregation tailored to timestamped data (TimescaleDB, InfluxDB, etc.) |
| DID | Decentralized Identifier | Decentralized identifier (W3C standard) controlled by the subject itself |
| Federated learning | Federated Learning | Mechanism for jointly training a model across parties without uploading raw data |
| Digital twin | Digital Twin | Real-time mirror and simulation of a physical entity in digital space |
| ISA-95 | ISA-95 | International standard layered model (L0–L4) for enterprise–control system integration |
| V2X | Vehicle-to-Everything | Umbrella term for vehicle-to-vehicle/road/network/person communication (C-V2X/DSRC) |
| RSU/OBU | Roadside Unit / On-Board Unit | Roadside communication unit / in-vehicle communication unit |
| Edge computing | Edge Computing | Performing computation and decision-making close to the data source |

## B. References

1. 3GPP TS 22.261 — 5G system service requirements (including IoT scenarios)
2. 3GPP TS 36.300 — LTE/4G system architecture (overall E-UTRA description)
3. 3GPP TS 38.300 — Overall description of the 5G NR system architecture
4. 3GPP TR 38.875 (RedCap study report) / TR 38.821 (NTN non-terrestrial network study report)
5. CSA, *Matter Specification* — Unified application-layer standard for smart homes
6. OASIS, *MQTT Version 5.0* — Message Queuing Telemetry Transport
7. IETF, *RFC 7252 (CoAP)* / *draft-ietf-oauth-v2-1 (OAuth 2.1 draft, not yet finalized)* / *RFC 8628 (device authorization flow)*
8. Anthropic / Agentic AI Foundation, *Model Context Protocol (MCP) Specification* — Open standard for AI–tool interaction
9. Spring reference documentation — *Spring Boot 4.0 (GA 2025-11) / Spring Cloud 2025.1 (GA 2025-11) / Spring AI 2.0 (GA 2026-06)*
10. IoT Analytics, *State of IoT* — Global installed base of IoT devices and industry data
11. LoRa Alliance, *LoRaWAN L2 1.0.4 / 1.1* and *Regional Parameters RP-002-1.0.5 (2025-10)*
12. IoT DC3 open-source project — https://gitee.com/pnoker/iot-dc3 (running case throughout the book)

## C. Index

**Protocols & communication**: MQTT / CoAP / LwM2M / Modbus / OPC UA / NB-IoT / LoRa(WAN) / 5G (RedCap/NTN) / Wi-Fi / BLE / Zigbee / Matter / Thread / gRPC / REST

**Architecture & platform**: Five-layer architecture / intelligence layer / microservices / Gateway / Auth / Manager / Data / Agentic / thing model / point value / device shadow / time-series database / message queue / rule engine / edge-cloud collaboration

**AI & agents**: Large language model (LLM) / Agent / RAG / Tool calling / MCP / Spring AI / Agentic Center / natural-language operations / anomaly detection / predictive maintenance / TSFM / on-device SLM

**Security**: OAuth 2.1 (IETF draft) / JWT / X.509 certificates / TLS 1.3 / DTLS / RBAC / ABAC / multi-tenancy / prompt injection / PQC (post-quantum cryptography)

**Application scenarios**: Industrial IoT (IIoT) / digital twins / smart cities / connected vehicles (V2X) / precision agriculture / blockchain + IoT / supply-chain traceability
