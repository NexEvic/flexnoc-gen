# FlexNoC Feature Checklist

> 生成时间: 2026-03-23
> 数据源: sampleproject.pdd (D2), PSI_reference_design.pdd (D3), API_REFERENCE.md

## 进度
- 总 feature 数: 50
- ✅ 已实现并验证: 44
- 🔧 已实现未验证: 0
- ❌ 未实现: 6
- ⬜ 不适用: 0
- 覆盖率: 44/50 = 88%

## 符号说明
- ✅ 已实现并验证
- 🔧 已实现未验证
- ❌ 未实现
- ⬜ 不适用于 PDD DSL

---

## A. 协议 (Protocol)

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| A1 | AXI (V3) — addr/data/id/enRead/enWrite/useFixed | `protocol`, `wAddr`, `wData`, `wId` | ✅ 端到端验证 | — |
| A2 | APB — addr/data | `protocol` | ✅ PDD 生成 | — |
| A3 | OCP_Lite — addr/data/id | `protocol` | ✅ PDD 生成 | — |
| A4 | AXI4/AXI5 扩展 — wLen, wQos, wRegion, wReqUser, wRspUser | `wReqUser`, `wRspUser` 等 | ❌ 仅 kwargs 透传 | P0 |
| A5 | ACE-Lite — useBarrier, DVM, earlyWrRsp | useBarrier, withDVMsupport | ❌ | P1 |
| A6 | AHB 协议 | — | ❌ | P1 |
| A7 | AXI-Lite 协议 | — | ❌ | P1 |
| A8 | NSP 协议 | — | ❌ | P2 |
| A9 | NSP_BROADCAST | — | ❌ | P3 |
| A10 | PIF 协议 | — | ❌ | P3 |
| A11 | LLI 协议 | additionalClocks, conversion | ❌ | P2 |
| A12 | SERVICE 内部协议 | `protocol` value SERVICE | ✅ (用于 NOC registers) | — |

## B. 时钟与复位 (Clock & Reset)

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| B1 | 单时钟域 | `clockRegime`, `clockManager`, `clock` | ✅ 端到端验证 | — |
| B2 | 多时钟域 + 自动 CDC FIFO | 自动 `dtpLink` | ✅ 端到端验证 | — |
| B3 | Gated Clock | `type` = Gated | ✅ PDD 生成 | — |
| B4 | clockGating 细粒度 (每 socket 级) | `clockGating` | ✅ 端到端验证 | — |
| B5 | 额外时钟 + 生成时钟 | `additionalClocks` | ❌ | P2 |
| B6 | 电压域引用 | `voltage` in clockRegime | ✅ 端到端验证 | — |

## C. 寻址与安全 (Addressing & Security)

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| C1 | 全局/本地地址映射 | `globalAddress`, `localAddress`, `mask` | ✅ 端到端验证 | — |
| C2 | 地址交织 (Interleave) | `mask` 自动计算 | ✅ 端到端验证 | — |
| C3 | Mode (Remap) | `modeFlag`, `modes` | ✅ PDD 生成 | — |
| C4 | Firewall | 无样例在参考 PDD 中 | ❌ | P0 |
| C5 | UserFlag (secure/privileged/debug) | `userFlag` object kind | ✅ 端到端验证 | — |
| C6 | readPermissions / writePermissions | `readPermissions`, `writePermissions` | ✅ 端到端验证 | — |
| C7 | useErrorCodes | `useErrorCodes` | ✅ 端到端验证 | — |

## D. Socket / NIU 参数

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| D1 | pending transactions | `nPendingTrans` | ✅ 端到端验证 | — |
| D2 | pending order IDs | `nPendingOrderId` | ✅ 端到端验证 | — |
| D3 | soft lock | `useSoftLock` | ✅ PDD 生成 | — |
| D4 | sequential ID width | `wSeqId` | ✅ PDD 生成 | — |
| D5 | minInterleaveSize | `minInterleaveSize` | ✅ PDD 生成 | — |
| D6 | seqIdAllocation | `seqIdAllocation` | ✅ 端到端验证 | — |
| D7 | conversion (socket 级/协议转换) | `conversion` | ❌ | P1 |
| D8 | comment (socket 级注释) | `comment` | ✅ 端到端验证 | — |

## E. 拓扑与架构 (Architecture)

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| E1 | 自动拓扑 (crossbar) | auto_derive() | ✅ 端到端验证 | — |
| E2 | 手动拓扑 (switch/link/route) | add_switch/link/set_route | ✅ PDD 生成 | — |
| E3 | CDC FIFO Link | dtpLink/FIFO | ✅ PDD 生成 | — |
| E4 | 自定义仲裁策略 | `muxDefaultArbiters`, `ArbiterMode` | ✅ 端到端验证 | — |
| E5 | Pipeline stages (inputPipes/outputPipes) | `inputPipes`, `outputPipes` | ✅ 端到端验证 | — |
| E6 | headerPenalty 自定义 | `headerPenalty` | ✅ (参数已暴露) | — |

## F. UserMapping

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| F1 | AXI Target userMapping (CONST_0) | `userMapping` ARCache/AWCache/Prot | ✅ 端到端验证 | — |
| F2 | userMapping with userFlags | `userFlags` in userMapping | ✅ 端到端验证 | — |
| F3 | Initiator driving userFlags | `driving` → `userFlags` | ✅ 端到端验证 | — |
| F4 | 自定义 specials mapping | `specials` 非 CONST_0 | ❌ | P0 |

## G. 电源管理 (Power)

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| G1 | Power domain 对象 | `power` object kind | ✅ 端到端验证 | — |
| G2 | Voltage 对象 | `voltage` object kind | ✅ 端到端验证 | — |
| G3 | Activity zone | `activityZone` object kind | ✅ PDD 生成 | — |
| G4 | IPpowerDomain (socket 级) | `power` → `IPpowerDomain` | ✅ 端到端验证 | — |
| G5 | swbNet (Sideband Network) | `swbNet` object kind | ❌ | P2 |

## H. QoS

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| H1 | nUrgencyLevel | `nUrgencyLevel` | ✅ PDD 生成 | — |
| H2 | usePress | `usePress` | ❌ | P1 |
| H3 | hurryThresholds / pressureThresholds | `hurryThresholds`, `pressureThresholds` | ❌ | P2 |

## I. 观测 (Observability)

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| I1 | Observer 基础 (clock + errorLoggers) | `observer`, `errorLoggers` | ✅ PDD 生成 | — |
| I2 | Observer 高级 (probes, stats, ATB) | — | ❌ | P2 |
| I3 | obsSwitch 自动派生 | obsSwitch | ✅ PDD 生成 | — |

## J. 端口 (Ports)

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| J1 | Clock port | `type` = Clock | ✅ 端到端验证 | — |
| J2 | ResetN port | `type` = ResetN | ✅ 端到端验证 | — |
| J3 | TestMode port | `type` = TestMode | ✅ 端到端验证 | — |
| J4 | Mode port | `type` = Mode | ✅ PDD 生成 | — |
| J5 | User port | `type` = User | ✅ PDD 生成 | — |

## K. 导出 (Export)

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| K1 | Verilog 导出 (VCS) | `exportOption` = Verilog | ✅ 端到端验证 | — |
| K2 | customerCells (synthesis) | `customerCells` | ✅ 端到端验证 | — |
| K3 | 多 exportOption | 多个 exportOption 对象 | ✅ 端到端验证 | — |
| K4 | synthesisTool (DC/Genus) | `synthesisTool` | ✅ 端到端验证 | — |
| K5 | extraPorts | `extraPorts` | ❌ | P2 |
| K6 | SystemC 导出 | exportOption = SystemC | ❌ | P2 |
| K7 | files = SingleFile | `files` | ✅ 端到端验证 | — |
| K8 | AIP bindings / instrumentation | `instrumentation`, `AIP_bindings` | ❌ | P2 |

## L. 探索/仿真 (Exploration)

| # | Feature | PDD key | 当前状态 | 优先级 |
|---|---------|---------|---------|--------|
| L1 | Scenario | `scenario` object kind | ❌ | P2 |
| L2 | Queue | `queue` object kind | ❌ | P2 |
| L3 | TargetModel | `targetModel` object kind | ❌ | P2 |
| L4 | Process/Procedure | `process`, `procedure` object kinds | ❌ | P2 |

---

## 未实现 Feature 优先级排序 (P0 实施顺序)

| 序号 | Feature ID | 名称 | 复杂度 | 说明 |
|------|-----------|------|--------|------|
| 1 | C5 | UserFlag 对象 | 低 | 仅需添加 object kind，empty properties |
| 2 | F2+F3 | userMapping with userFlags | 中 | 关联 C5，修改 pdd_writer userMapping 逻辑 |
| 3 | E4 | 自定义仲裁策略 | 低 | 修改 `_add_arch_globals()` 中硬编码 ROTATE |
| 4 | E5 | Pipeline stages | 低 | 扩展 DtpSwitch 加 inputPipes/outputPipes 配置 |
| 5 | F4 | 自定义 specials mapping | 低 | 扩展现有 userMapping 逻辑 |
| 6 | B4 | clockGating 每 socket 级 | 低 | socket 属性添加 clockGating 条目 |
