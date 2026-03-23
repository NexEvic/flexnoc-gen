# Protocol API

> 模块: `flexnoc_dsl.protocol`
> 职责: 定义 NoC 中各 socket 使用的总线协议（AXI、APB、OCP、AHB 等）

---

## 1. 概述

每个 NoC 设计必须至少有一个协议定义。协议通过工厂函数创建，再通过 `noc.add_protocol(name, proto)` 注册到项目中。
一个协议可以被多个 socket 共享引用。

**工作流**:
```python
axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64, id=4))
# → 在 PDD 中生成 <object kind="protocol" name="AXI_prot">
```

## 2. Protocol dataclass

```python
@dataclass
class Protocol:
    name: str = ""              # 由 add_protocol() 自动填充，不需手动设置
    protocol_type: str = ""     # PDD protocol 值: "AXI", "APB", "OCP_Lite", "AHB", "SERVICE"
    addr_width: int = 32        # → PDD entry key="wAddr"
    data_width: int = 64        # → PDD entry key="wData"
    id_width: int = 4           # → PDD entry key="wId"（仅 AXI/OCP 有效）
    en_read: bool = True        # → PDD entry key="enRead"（仅 AXI/OCP）
    en_write: bool = True       # → PDD entry key="enWrite"（仅 AXI/OCP）
    use_fixed: bool = False     # → PDD entry key="useFixed"（仅 AXI）
    extra: dict = {}            # → 任意额外 PDD entry (key-value)
```

## 3. 工厂函数

### 3.1 AXI()

创建 AXI (AMBA AXI V3 兼容) 协议。

```python
AXI(addr=32, data=64, id=4, read=True, write=True, fixed=False, **kwargs)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `addr` | int | 32 | 1–64 | `wAddr` | 地址总线宽度 (bits) |
| `data` | int | 64 | 8, 16, 32, 64, 128, 256, 512, 1024 | `wData` | 数据总线宽度 (bits)，必须为 2 的幂 |
| `id` | int | 4 | 0–32 | `wId` | Transaction ID 宽度 (bits)。0 = 无 ID |
| `read` | bool | True | True/False | `enRead` | 启用读通道 |
| `write` | bool | True | True/False | `enWrite` | 启用写通道 |
| `fixed` | bool | False | True/False | `useFixed` | 启用 FIXED burst 类型 |
| `**kwargs` | — | — | — | 直接输出 | 扩展字段 (见下表) |

**常用扩展字段 (`**kwargs`)**:

| 字段 | 类型 | 说明 | PDD key |
|------|------|------|---------|
| `wReqUser` | int | Request user signal 宽度 | `wReqUser` |
| `wRspUser` | int | Response user signal 宽度 | `wRspUser` |
| `wLen` | int | Burst length 字段宽度 (AXI4: 8) | `wLen` |
| `wQos` | int | QoS 字段宽度 | `wQos` |
| `wRegion` | int | Region 字段宽度 | `wRegion` |

**示例**:
```python
# 基础 AXI
axi = AXI(addr=32, data=64, id=4)

# AXI4 扩展
axi4 = AXI(addr=40, data=128, id=8, wReqUser=1, wRspUser=1)

# 只读 AXI
axi_ro = AXI(addr=32, data=64, id=4, read=True, write=False)
```

**PDD 输出**:
```xml
<object disabled="0" kind="protocol" name="AXI_prot">
  <properties>
    <entry key="protocol" value="AXI">
      <entry key="enRead" value="True"/>
      <entry key="enWrite" value="True"/>
      <entry key="useFixed" value="False"/>
      <entry key="wAddr" value="32"/>
      <entry key="wData" value="64"/>
      <entry key="wId" value="4"/>
    </entry>
  </properties>
</object>
```

### 3.2 APB()

创建 APB (AMBA APB) 协议。

```python
APB(addr=32, data=32, **kwargs)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `addr` | int | 32 | 1–64 | `wAddr` | 地址宽度 |
| `data` | int | 32 | 8, 16, 32 | `wData` | 数据宽度 |

**特性**:
- `id_width` 强制为 0（APB 无 transaction ID）
- PDD 不生成 `enRead`/`enWrite`/`useFixed`（AXI 特有）
- `protocol_type` = `"APB"`

### 3.3 OCP()

创建 OCP_Lite 协议。

```python
OCP(addr=32, data=64, id=4, **kwargs)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `addr` | int | 32 | 1–64 | `wAddr` | 地址宽度 |
| `data` | int | 64 | 8–1024 (2的幂) | `wData` | 数据宽度 |
| `id` | int | 4 | 0–32 | `wId` | Thread ID 宽度 |

**特性**:
- `protocol_type` = `"OCP_Lite"`
- 生成 `enRead`/`enWrite`/`useFixed` 条目（与 AXI 相同）

### 3.4 AHB()

创建 AHB (AMBA AHB) 协议。

```python
AHB(addr=32, data=32, **kwargs)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `addr` | int | 32 | 1–64 | `wAddr` | 地址宽度 |
| `data` | int | 32 | 8, 16, 32, 64 | `wData` | 数据宽度 |

**特性**:
- `id_width` 强制为 0
- PDD 不生成 `enRead`/`enWrite`/`useFixed`
- `protocol_type` = `"AHB"`

**AHB 特殊行为**:
- AHB target 自动生成 HProt userMapping：`HProt → CONST_0 #0,1,2,3` 和 `XorHProt_6 → CONST_0 #0`
- AHB target 的 `pending_trans` 最大值为 **1**（AHB 协议限制，不支持 outstanding transactions）
- 当 AXI initiator 连接到 AHB target 时，initiator shadow 自动添加 `nReassemblyBuffer=2`

**约束**:
- ⚠️ `pending_trans > 1` 会导致 FlexNoC 报错
- ⚠️ AHB 不支持 `useFixed`、`wId`、burst 扩展字段

### 3.5 AXI_Lite()

创建 AXI-Lite 协议（AXI 的极简子集，无 burst、无 ID）。

```python
AXI_Lite(addr=32, data=32, **kwargs)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `addr` | int | 32 | 1–64 | `wAddr` | 地址宽度 |
| `data` | int | 32 | 32, 64 | `wData` | 数据宽度 |

**特性**:
- `protocol_type` = `"AXI"`（PDD 层面与 AXI 相同）
- `id_width` 强制为 0（不生成 `wId`）
- `use_fixed` 强制为 False
- AXI-Lite target 的 userMapping 与标准 AXI 相同（ARCache/AWCache/Prot → CONST_0）

### 3.6 ACE_Lite()

创建 ACE-Lite (AXI Coherency Extension) 协议。

```python
ACE_Lite(addr=32, data=64, id=4, use_barrier=False, dvm=False,
         early_wr_rsp=False, **kwargs)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `addr` | int | 32 | 1–64 | `wAddr` | 地址宽度 |
| `data` | int | 64 | 8–1024 (2的幂) | `wData` | 数据宽度 |
| `id` | int | 4 | 0–32 | `wId` | ID 宽度 |
| `use_barrier` | bool | False | True/False | — | Barrier 事务支持 |
| `dvm` | bool | False | True/False | — | DVM 支持 |
| `early_wr_rsp` | bool | False | True/False | — | 早期写响应 |

**⚠️ FlexNoC 5.3.0 限制**:
- `use_barrier`、`dvm`、`early_wr_rsp` 参数在 PDD 中**不生效**
- 工厂函数生成标准 AXI 协议 (`protocol_type="AXI"`)
- 一致性参数保留接口，以备未来 FlexNoC 版本支持

## 4. 注册协议

```python
proto = noc.add_protocol(name: str, proto: Protocol) -> Protocol
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | str | 协议对象名（PDD 中的 `<object name="...">`）|
| `proto` | Protocol | 工厂函数返回的协议对象 |

**返回**: 注册后的 Protocol 对象（`name` 字段已填充）

**约束**:
- `name` 在项目内必须唯一
- 同一个 Protocol 对象不应注册多次（`name` 会被覆盖）
- 建议命名规范: `"AXI_prot"`, `"APB_ctrl"`, `"AHB_periph"`

## 5. PDD 生成规则

| 规则 | 说明 |
|------|------|
| **不生成 version 字段** | FlexNoC 5.3.0 使用 `enRead`/`enWrite` 替代 |
| **extra 透传** | `extra` dict 中的 key-value 直接作为 PDD `<entry>` 输出 |
| **id_width=0 跳过 wId** | APB、AHB、AXI-Lite 不生成 `wId` 条目 |
| **协议类型感知** | AHB/APB 不生成 `enRead`/`enWrite`/`useFixed`（仅 AXI/OCP） |
| **混合协议** | AXI init → AHB/APB target 时，init shadow 自动加 `nReassemblyBuffer=2` |

## 6. 协议与 Socket 的关系

```
Protocol (注册一次)
  ├── Initiator A (protocol=proto)  ← 引用
  ├── Initiator B (protocol=proto)  ← 引用
  ├── Target C (protocol=proto)     ← 引用
  └── Target D (protocol=other)     ← 可以不同协议
```

- 一个协议可被多个 socket 引用
- 不同 socket 可以引用不同协议（混合协议设计）
- PDD 中通过 `<entry key="reference" value="(project:AXI_prot)"/>` 引用

## 7. 冲突与约束

| 场景 | 约束 | 后果 |
|------|------|------|
| AHB target pending_trans > 1 | ❌ 禁止 | FlexNoC 导出报错 |
| AXI init → AHB target | 自动处理 | 添加 nReassemblyBuffer=2 |
| AXI init → APB target | 自动处理 | 添加 nReassemblyBuffer=2 |
| APB + useFixed | ❌ 无效 | APB 不支持 FIXED burst |
| AHB + wReqUser | ⚠️ 未验证 | 可能导致 FlexNoC 错误 |
| id_width=0 + seq_id_width=0 | ✅ 允许 | target 无 sequence ID |
