# noc2pdd API Reference

> FlexNoC Python DSL — 从 Python 代码生成 FlexNoC PDD 文件  
> 版本: 1.0 | 目标 FlexNoC: 5.3.0 | 已端到端验证

---

## 目录

1. [总览与快速开始](#1-总览与快速开始)
2. [Protocol API](#2-protocol-api)
3. [Clock API](#3-clock-api)
4. [Socket API (Initiator / Target / Flow / Mapping)](#4-socket-api)
5. [Port / ModeFlag / Observer API](#5-port--modeflag--observer-api)
6. [Architecture API (自动拓扑与手动拓扑)](#6-architecture-api)
7. [NocProject API (顶层入口)](#7-nocproject-api)
8. [端到端工作流](#8-端到端工作流)
9. [已支持 Feature 矩阵](#9-已支持-feature-矩阵)
10. [已知不支持 Feature](#10-已知不支持-feature)

---

## 1. 总览与快速开始

### 1.1 安装

```bash
cd ~/flexnoc-work/noc2pdd
# 无需 pip install，直接 import 即可
# 注意：如果 FlexNoC 的 bashrc 被 source 过，需要先清理环境
unset PYTHONHOME && unset PYTHONPATH
```

### 1.2 最小示例 (2x2 AXI Crossbar)

```python
from flexnoc_dsl import NocProject, AXI

noc = NocProject("xbar_2x2")
axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64, id=4))
clk = noc.add_clock("clk_domain", freq="500MHz")

noc.add_initiator("init_0", protocol=axi, clock=clk)
noc.add_initiator("init_1", protocol=axi, clock=clk)
noc.add_target("targ_0", protocol=axi, clock=clk, base=0x0, size="256M")
noc.add_target("targ_1", protocol=axi, clock=clk, base=0x10000000, size="256M")

noc.connect_all()
noc.set_export("Verilog", simulator="VCS")
noc.write_pdd("xbar_2x2.pdd")
```

**验证结果**: 上述代码生成 458 行 PDD → FlexNoC 导出 31,813 行 Verilog RTL ✅

### 1.3 设计哲学

- **Specification-only**: 用户只描述 "做什么" (socket、协议、连接)
- **Architecture 自动派生**: crossbar 拓扑 (switch/link/route) 全部自动计算
- **Structure 自动派生**: FlexNoC 通过 `-d False` 自动填充
- **手动覆盖**: 需要自定义拓扑时，可通过 `noc.architecture` 接口手动控制

---

## 2. Protocol API

### 2.1 模块: `flexnoc_dsl.protocol`

| 导出 | 类型 | 说明 |
|------|------|------|
| `Protocol` | dataclass | 协议基类 |
| `AXI()` | 工厂函数 | 创建 AXI 协议 |
| `APB()` | 工厂函数 | 创建 APB 协议 |
| `OCP()` | 工厂函数 | 创建 OCP_Lite 协议 |
| `AHB()` | 工厂函数 | 创建 AHB 协议 |
| `AXI_Lite()` | 工厂函数 | 创建 AXI-Lite 协议 (AXI 子集，无 burst/ID) |
| `ACE_Lite()` | 工厂函数 | 创建 ACE-Lite 协议 (AXI 一致性扩展) |

### 2.2 Protocol dataclass

```python
@dataclass
class Protocol:
    name: str = ""              # 由 add_protocol() 自动填充
    protocol_type: str = ""     # "AXI", "APB", "OCP_Lite", "SERVICE"
    addr_width: int = 32        # wAddr
    data_width: int = 64        # wData
    id_width: int = 4           # wId (AXI/OCP 有效，APB 忽略)
    en_read: bool = True        # enRead
    en_write: bool = True       # enWrite
    use_fixed: bool = False     # useFixed (AXI FIXED burst)
    extra: dict = {}            # 任意额外 PDD entry，如 wReqUser, wRspUser
```

### 2.3 工厂函数

#### `AXI(addr, data, id, read, write, fixed, **kwargs)`

| 参数 | 类型 | 默认值 | 说明 | PDD 对应 |
|------|------|--------|------|---------|
| `addr` | int | 32 | 地址宽度 | `wAddr` |
| `data` | int | 64 | 数据宽度 | `wData` |
| `id` | int | 4 | ID 宽度 | `wId` |
| `read` | bool | True | 启用读 | `enRead` |
| `write` | bool | True | 启用写 | `enWrite` |
| `fixed` | bool | False | FIXED burst | `useFixed` |
| `**kwargs` | | | 扩展字段 | 直接输出为 PDD entry |

**扩展字段示例**:
```python
AXI(addr=32, data=64, id=8, wReqUser=1, wRspUser=1)
# → PDD 中额外生成 <entry key="wReqUser" value="1"/>
```

#### `APB(addr, data, **kwargs)`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `addr` | int | 32 | 地址宽度 |
| `data` | int | 32 | 数据宽度 |

APB 无 ID 宽度 (`id_width=0`)。

#### `OCP(addr, data, id, **kwargs)`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `addr` | int | 32 | 地址宽度 |
| `data` | int | 64 | 数据宽度 |
| `id` | int | 4 | Thread ID 宽度 |

实际 PDD `protocol_type` 为 `"OCP_Lite"`。

#### `AHB(addr, data, **kwargs)`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `addr` | int | 32 | 地址宽度 |
| `data` | int | 32 | 数据宽度 |

AHB 协议无 ID 宽度 (`id_width=0`)。PDD `protocol_type` 为 `"AHB"`。

**AHB 特殊行为**:
- PDD 不生成 `enRead`/`enWrite`/`useFixed` (AXI-specific)
- Target 自动生成 HProt (`#0,1,2,3` → CONST_0) 和 XorHProt_6 (`#0` → CONST_0) userMapping
- `nPendingTrans` 最大值为 1 (AHB 限制)

#### `AXI_Lite(addr, data, **kwargs)`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `addr` | int | 32 | 地址宽度 |
| `data` | int | 32 | 数据宽度 |

AXI-Lite 是 AXI 的子集：无 burst、无 ID。PDD `protocol_type` 为 `"AXI"`，`id_width=0`。

#### `ACE_Lite(addr, data, id, use_barrier, dvm, early_wr_rsp, **kwargs)`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `addr` | int | 32 | 地址宽度 |
| `data` | int | 64 | 数据宽度 |
| `id` | int | 4 | ID 宽度 |
| `use_barrier` | bool | False | Barrier 事务 (5.3.0 不支持协议级) |
| `dvm` | bool | False | DVM 支持 (5.3.0 不支持协议级) |
| `early_wr_rsp` | bool | False | 早期写响应 (5.3.0 不支持协议级) |

ACE-Lite 工厂函数生成标准 AXI 协议 (`protocol_type="AXI"`)。
一致性参数 (`use_barrier`, `dvm`, `early_wr_rsp`) 在 FlexNoC 5.3.0 中不支持在协议级配置，工厂函数保留参数接口以备未来版本使用。

### 2.4 PDD 生成规则

- **不生成 `version` 字段** — FlexNoC 5.3.0 使用 `enRead`/`enWrite` 替代
- `extra` 中的 key-value 直接输出为 PDD `<entry>`
- `id_width=0` 时不生成 `wId` 字段
- **协议类型感知**: AHB/APB 协议不生成 `enRead`/`enWrite`/`useFixed` (仅 AXI/OCP 生成)
- **混合协议**: 当 AXI initiator 连接到 AHB/APB target 时，initiator shadow 自动添加 `nReassemblyBuffer=2`

---

## 3. Clock API

### 3.1 模块: `flexnoc_dsl.clock`

| 导出 | 类型 | 说明 |
|------|------|------|
| `ClockDomain` | dataclass | 时钟域定义 |

### 3.2 ClockDomain dataclass

```python
@dataclass
class ClockDomain:
    name: str               # 时钟域名 (也是 clockRegime 名)
    frequency: float        # 频率 (Hz)，由 _parse_freq 解析
    port_name: str          # Clock 端口名 → PDD port(kind=Clock)
    reset_name: str         # ResetN 端口名 → PDD port(kind=ResetN)
    test_mode: str = "Tm"   # TestMode 端口名 → PDD port(kind=TestMode)
    manager_name: str = "Cm"  # ClockManager 名
    clock_name: str = "Clk"   # Clock 对象名
    clock_type: str = "Root"  # "Root" 或 "Gated"
    voltage_ref: str = ""     # 电压域引用 (→ PDD clockRegime/voltage)
    comment: str = ""         # 注释 (→ PDD clockRegime/comment)
    power_ref: str = ""       # 电源域引用 (→ PDD clockRegime/power)
```

### 3.3 通过 NocProject 创建

```python
clk = noc.add_clock(name, freq, port, reset, test_mode, clock_type,
                    voltage_ref, comment, power_ref)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | (必填) | 时钟域名 |
| `freq` | str/int/float | `"500MHz"` | 频率，支持 Hz/KHz/MHz/GHz 后缀 |
| `port` | str | `"clk"` | 时钟端口名 |
| `reset` | str | `"rst_n"` | 复位端口名 |
| `test_mode` | str | `"Tm"` | TestMode 端口名 |
| `clock_type` | str | `"Root"` | 时钟类型 |
| `voltage_ref` | str | `""` | 电压域引用 (→ clockRegime `voltage` entry) |
| `comment` | str | `""` | 注释 (→ clockRegime `comment` entry) |
| `power_ref` | str | `""` | 电源域/活动区域引用，如 `"NoC_dom/NoC_zone"` |

### 3.4 频率解析

```python
"500MHz"  → 500000000.0
"1GHz"    → 1000000000.0
"100KHz"  → 100000.0
"266e6"   → 266000000.0
266000000 → 266000000.0
```

### 3.5 引用路径

| 属性 | 格式 | 用途 |
|------|------|------|
| `clock_ref` | `(specification:name/Cm/Clk)` | specification 层引用 |
| `arch_clock_ref` | `(switchBasedArchitecture:name/Cm/Clk)` | architecture 层引用 |

### 3.6 PDD 生成效果

每个 ClockDomain 自动生成:
- 1 个 `clockRegime` 对象 (含 frequency)
- 1 个 `clockManager` 对象 (含 resetN/rootClock/testMode 引用)
- 1 个 `clock` 对象 (含 type=Root/Gated)
- 1 个 `port`(Clock 类型) + 1 个 `port`(ResetN 类型) + 1 个 `port`(TestMode 类型，共享)

### 3.7 多时钟域支持

```python
clk_a = noc.add_clock("domain_a", "500MHz", port="clk_a", reset="rst_a_n")
clk_b = noc.add_clock("domain_b", "200MHz", port="clk_b", reset="rst_b_n")

noc.add_initiator("init_0", protocol=axi, clock=clk_a)
noc.add_target("targ_0", protocol=axi, clock=clk_b)
# → 自动生成 CDC FIFO dtpLink
```

多个时钟域共享同一个 TestMode 端口 (`Tm`)，DSL 自动去重。

---

## 4. Socket API (Initiator / Target / Flow / Mapping)

### 4.1 模块: `flexnoc_dsl.socket`

| 导出 | 类型 | 说明 |
|------|------|------|
| `Initiator` | dataclass | 发起方 socket |
| `Target` | dataclass | 接收方 socket |
| `Flow` | dataclass | 数据流 (initiator/target 下) |
| `Mapping` | dataclass | 地址映射 (flow 下) |

### 4.2 Initiator — 通过 NocProject 创建

```python
init = noc.add_initiator(name, protocol, clock, pending_trans, pending_ids,
                         use_soft_lock, use_press, clock_gating, comment,
                         power_domain, conversion)
```

| 参数 | 类型 | 默认值 | 说明 | PDD 对应 |
|------|------|--------|------|---------|
| `name` | str | (必填) | 接口名 | `socket name` |
| `protocol` | Protocol | None | 协议对象 | `protocol reference` |
| `clock` | ClockDomain | None | 时钟域 | `clock` entry |
| `pending_trans` | int | 4 | 未完成事务数 | architecture shadow `nPendingTrans` |
| `pending_ids` | int | 1 | 未完成排序 ID 数 | architecture shadow `nPendingOrderId` |
| `use_soft_lock` | bool | False | 软锁 | `parameters/useSoftLock` |
| `use_press` | bool | False | QoS 压力信号 | `parameters/usePress` |
| `clock_gating` | str | `""` | 时钟门控 (`""`, `"#Common"`, 或自定义) | `clockGating` |
| `comment` | str | `""` | Socket 注释 | `comment` |
| `power_domain` | str | `""` | 电源域引用 | architecture shadow `power/IPpowerDomain` |
| `conversion` | dict | `{}` | 协议转换配置 | `conversion` entry (空或自定义) |

**返回**: `Initiator` 对象

**usePress 效果**: 当 `use_press=True` 时，自动生成:
- specification 层: `press` 端口 (User/Input, width=nUrgencyLevel, defaultVal=0)
- architecture 层: `press` shadow 条目
- structure 层: `press` shadow 条目 + `tacticalPorts/main/Press` 映射

**conversion 效果**: 生成 PDD `conversion` entry。空 dict (`{}`) 生成空 `<entry key="conversion"/>`，
有值则生成 `<entry key="conversion"><entry key="xxx" value="yyy"/>...</entry>`。

**混合协议 nReassemblyBuffer**: 当 AXI initiator 连接到 AHB/APB target 时，
architecture shadow 自动添加 `nReassemblyBuffer=2`。

### 4.3 Target — 通过 NocProject 创建

```python
targ = noc.add_target(name, protocol, clock, base, size, pending_trans, seq_id_width, use_soft_lock)
```

| 参数 | 类型 | 默认值 | 说明 | PDD 对应 |
|------|------|--------|------|---------|
| `name` | str | (必填) | 接口名 | `socket name` |
| `protocol` | Protocol | None | 协议对象 | `protocol reference` |
| `clock` | ClockDomain | None | 时钟域 | `clock` entry |
| `base` | int | 0 | 基地址 | `globalAddress` |
| `size` | str/int | "0" | 地址空间大小 | 计算 `mask` |
| `pending_trans` | int | 16 | 未完成事务数 | `nPendingTrans` |
| `seq_id_width` | int | 0 | 序列 ID 宽度 (0=用协议的 id_width) | `wSeqId` |
| `use_soft_lock` | bool | False | 软锁 | `useSoftLock` |

**返回**: `Target` 对象

#### Size 解析

```python
size="256M"  → 268435456 (256 × 1024²)
size="1G"    → 1073741824
size="4K"    → 4096
size="0x1000" → 4096
size=65536   → 65536
```

支持后缀: `K` (1024), `M` (1M), `G` (1G), `T` (1T)

#### AXI Target 自动 userMapping

当协议类型为 AXI 时，Target socket 自动生成 `userMapping`:
- `ARCache` → `CONST_0 #0,1,2,3`
- `AWCache` → `CONST_0 #0,1,2,3`
- `Prot` → `CONST_0 #0,1,2`

### 4.4 Flow — 数据流

每个 Initiator/Target 下有 1 个或多个 Flow。**默认自动创建 flow "0"**。

#### 访问/创建 Flow

```python
init = noc.add_initiator("init_0", protocol=axi, clock=clk)

# 自动 flow (无需手动创建):
# add_initiator 后，_finalize() 时自动创建 flow "0"

# 手动获取/创建多个 flow:
flow0 = init.flow(0)  # 获取 flow "0"，不存在则创建
flow1 = init.flow(1)  # 获取 flow "1"，不存在则创建
```

#### Flow dataclass

```python
@dataclass
class Flow:
    name: str = "0"                    # flow 名 (通常 "0", "1", ...)
    mappings: list[Mapping] = []       # 地址映射列表
    default_error_target: str = ""     # 默认错误目标 (PDD: defaultErrorTarget)
```

#### 添加 Mapping

```python
flow = init.flow(0)
flow.add_mapping(
    name="region_0",          # mapping 名 (默认自增序号)
    base=0x0000_0000,         # 全局基地址 → globalAddress
    size="256M",              # 大小 → 计算 mask
    local_address=0x0,        # 本地地址 → localAddress
    access="ReadWrite",       # 访问类型 (未直接输出到 PDD，预留)
    mode={boot_flag: False},  # 模式条件 → modes entry
    comment="DRAM region"     # 注释 → comment entry
)
```

### 4.5 Mapping dataclass

```python
@dataclass
class Mapping:
    name: str                      # mapping 名
    global_address: int = 0        # → PDD globalAddress (十进制)
    local_address: int = 0         # → PDD localAddress
    mask: int = 0                  # → PDD mask (显式设置时优先)
    size: int = 0                  # 自动转为 mask (mask = size - 1)
    access: str = "ReadWrite"      # 预留字段
    modes: dict = {}               # {ModeFlag对象或名称: bool} → PDD modes
    comment: str = ""              # → PDD comment
```

**Mask 计算**: `effective_mask()` 返回 `mask` (显式) 或 `size - 1` (由 size 推导)

### 4.6 多 Flow / 多 Mapping 示例 (Remap)

```python
# 场景: init_0 有两个 flow，通过 boot_mode flag 切换地址映射
boot = noc.add_mode_flag("boot_mode", port="boot_sel", active_value=1)

init = noc.add_initiator("init_0", protocol=axi, clock=clk)
flow0 = init.flow(0)

# Boot 模式: 访问 ROM
flow0.add_mapping("boot_rom", base=0x0, size="64K",
                   mode={boot: True}, comment="Boot ROM mapping")

# Normal 模式: 访问 DRAM
flow0.add_mapping("dram", base=0x0, size="256M",
                   mode={boot: False}, comment="DRAM mapping")
```

**PDD 输出**:
```xml
<object kind="mapping" name="boot_rom">
  <properties>
    <entry key="globalAddress" value="0"/>
    <entry key="localAddress" value="0"/>
    <entry key="mask" value="65535"/>
    <entry key="modes">
      <entry key="(specification:boot_mode)" value="True"/>
    </entry>
  </properties>
</object>
```

### 4.7 自动 Flow 行为

如果用户**没有**手动创建 flow/mapping，`_finalize()` 时自动:

| Socket 类型 | 自动行为 |
|------------|---------|
| **Initiator** | 创建 flow "0"，mapping "0"，mask = 所有连接 target 地址空间并集 |
| **Target** | 创建 flow "0"，mapping "0"，globalAddress = base_address, mask = size - 1 |

### 4.8 Connectivity (连接矩阵)

```python
# 全连接 (所有 initiator → 所有 target)
noc.connect_all()

# 选择性连接
noc.connect("init_0", ["targ_0", "targ_1"])
noc.connect("init_1", ["targ_1"])     # init_1 只能访问 targ_1

# 断开特定连接
noc.disconnect("init_0", "targ_1")    # init_0 不能再访问 targ_1
```

**PDD 对应**: `specification/properties/connectivity` 矩阵中的 True/False 条目

### 4.9 地址交织 (Address Interleaving)

FlexNoC 支持两种 interleave：
- **地址交织 (Striped Mapping)**: 将连续地址空间按固定粒度在多个 target 间轮转分配
- **响应交织 (Response Interleaving)**: AXI 协议层面，控制读响应数据的交织粒度

#### 4.9.1 地址交织 — 通过 NocProject 创建

```python
targets = noc.add_interleaved_targets(
    names=["DDR0", "DDR1"],          # target 名列表 (数量必须是 2 的幂)
    protocol=axi,                     # 共享协议
    clock=clk,                        # 共享时钟域
    total_base=0,                     # 交织区域起始地址
    total_size="2G",                  # 交织区域总大小
    stripe_size="1K",                 # 交织粒度 (每个 stripe 的字节数)
    pending_trans=16,                 # 每个 target 的未完成事务数
    min_interleave_size=0,            # 响应交织大小 (0=禁用)
)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `names` | list[str] | (必填) | target 名列表，数量须为 2 的幂 |
| `protocol` | Protocol | None | 共享协议对象 |
| `clock` | ClockDomain | None | 共享时钟域 |
| `total_base` | int | 0 | 交织区域在全局地址空间的起始地址 |
| `total_size` | str/int | "0" | 交织区域总大小 |
| `stripe_size` | str/int | "4K" | 交织粒度 (须为 2 的幂) |
| `pending_trans` | int | 16 | 每 target 未完成事务数 |
| `seq_id_width` | int | 0 | wSeqId |
| `min_interleave_size` | int | -1 | 响应交织大小 (-1=不输出, 0=禁用) |
| `access` | str | "ReadWrite" | 访问类型 |

**返回**: `list[Target]` — 创建的所有 Target 对象

#### 地址交织原理

FlexNoC 通过 mapping 的 mask 字段实现地址交织。传统 compact mapping 的 mask 是连续的低位 1:
```
compact mask: 0x0FFF_FFFF (256MB，bits 0-27 全为 1)
```

交织 (striped) mapping 的 mask 在 stripe 位置有 0 bit，用于选择 target：
```
stripe mask:  0x7FFF_FBFF (2GB 2-way 1KB stripe，bit 10 = 0)
```

选择规则：mask 中为 0 的 bit 与 globalAddress 比较，匹配则路由到对应 target。

#### DDR 2-way 1KB Interleave 示例

```
全局地址     Target   说明
0x000-0x3FF  DDR0     stripe 0 (bit10=0)
0x400-0x7FF  DDR1     stripe 1 (bit10=1)
0x800-0xBFF  DDR0     stripe 2 (bit10=0)
0xC00-0xFFF  DDR1     stripe 3 (bit10=1)
...
```

PDD 中生成的 mapping：
```xml
<!-- DDR0: bit 10 = 0 的地址 -->
<object kind="mapping" name="0">
  <properties>
    <entry key="globalAddress" value="0"/>
    <entry key="localAddress" value="0"/>
    <entry key="mask" value="2147482623"/>  <!-- 0x7FFF_FBFF -->
  </properties>
</object>

<!-- DDR1: bit 10 = 1 的地址 -->
<object kind="mapping" name="0">
  <properties>
    <entry key="globalAddress" value="1024"/>  <!-- 0x400 = 1 << 10 -->
    <entry key="localAddress" value="0"/>
    <entry key="mask" value="2147482623"/>
  </properties>
</object>
```

**验证结果**: 上述配置生成 PDD → FlexNoC 导出 28,117 行 Verilog RTL ✅

#### 4-way DDR Interleave 示例

```python
targets = noc.add_interleaved_targets(
    names=["DDR0", "DDR1", "DDR2", "DDR3"],
    protocol=axi, clock=clk,
    total_size="4G",
    stripe_size="4K",   # 4KB stripe (页对齐)
)
```

#### 4.9.2 响应交织 — minInterleaveSize 参数

`min_interleave_size` 控制 AXI 读响应在 R channel 上的交织粒度：

| 值 | 含义 |
|---|------|
| -1 (默认) | 不输出该参数 (FlexNoC 使用默认值) |
| 0 | 禁用读响应交织 (target 不会交织 RD/WR 响应) |
| wData/8 | 字级交织 (每个数据字后可插入其他响应) |
| N × wData/8 | 多字交织 (每 N 字后才允许交织) |

Initiator 和 Target 均可设置：

```python
# Initiator — 控制 initiator 端的交织行为
noc.add_initiator("CPU", protocol=axi, clock=clk, min_interleave_size=0)

# Target — 控制 target 端的交织行为
noc.add_target("SRAM", protocol=axi, clock=clk, base=0x0, size="1M",
               min_interleave_size=8)  # 8 bytes = wData/8 for 64-bit
```

#### 4.9.3 低级 API: 手动计算交织 mask

```python
from flexnoc_dsl import compute_interleave_mask, create_interleaved_mappings

# 计算交织 mask
mask = compute_interleave_mask(
    per_target_size=1 << 30,  # 1GB per DDR
    stripe_size=1024,          # 1KB stripe
    num_targets=2,             # 2-way
)
# mask = 0x7FFF_FBFF

# 生成完整 mapping 列表
all_mappings = create_interleaved_mappings(
    num_targets=2,
    stripe_size=1024,
    total_size=2 << 30,        # 2GB total
    base_address=0,
)
# all_mappings[0] = [Mapping(global_addr=0, mask=0x7FFFFBFF, ...)]
# all_mappings[1] = [Mapping(global_addr=0x400, mask=0x7FFFFBFF, ...)]
```

---

## 5. Port / ModeFlag / Observer API

### 5.1 模块: `flexnoc_dsl.port`

| 导出 | 类型 | 说明 |
|------|------|------|
| `Port` | dataclass | 端口定义 |
| `ModeFlag` | dataclass | 模式标志 (Boot/Remap 等) |
| `Observer` | dataclass | 错误观察器 |

### 5.2 Port dataclass

```python
@dataclass
class Port:
    name: str                     # 端口名
    port_type: str                # "Clock", "ResetN", "TestMode", "Mode", "User"
    clock_ref: str = ""           # 时钟引用 ("None" 表示异步)
    width: int = 1                # 位宽
    direction: str = ""           # "Input" / "Output" (仅 User 类型)
    default_val: int | None = None  # 仿真默认值
```

**注意**: Clock/ResetN/TestMode 端口由 `add_clock()` 自动创建，无需手动添加。

#### 用户自定义端口

```python
noc.add_user_port(name, direction, width, clock, default)
```

| 参数 | 类型 | 默认值 | 说明 | PDD 对应 |
|------|------|--------|------|---------|
| `name` | str | (必填) | 端口名 | port name |
| `direction` | str | `"Input"` | 方向 | type/direction |
| `width` | int | 1 | 位宽 | type/width |
| `clock` | ClockDomain | None | 时钟域 (None="None") | type/clock |
| `default` | int | None | 仿真默认值 | simulationModel/defaultVal |

```python
# 示例: 添加 interrupt 输出端口
noc.add_user_port("irq_out", direction="Output", width=1, clock=clk)

# 示例: 添加带仿真默认值的输入端口
noc.add_user_port("cfg_sel", direction="Input", width=4, clock=clk, default=0)
```

**PDD 输出**: `<object kind="port">` with `type=User`

### 5.3 ModeFlag — 模式标志

用于地址 remap: 一个物理端口驱动一个逻辑标志，mapping 根据标志值选择不同地址。

```python
mf = noc.add_mode_flag(name, port, active_value)
```

| 参数 | 类型 | 默认值 | 说明 | PDD 对应 |
|------|------|--------|------|---------|
| `name` | str | (必填) | 逻辑标志名 | modeFlag name |
| `port` | str | `name.lower()` | 驱动端口名 | port(kind=Mode) name |
| `active_value` | int | 1 | 激活值 | modePortValues |

**PDD 生成**:
- 1 个 `<object kind="modeFlag">` (含 modePortValues)
- 1 个 `<object kind="port">` (kind=Mode, 如果不存在)

**使用方式**: 在 `flow.add_mapping(mode={mf: True/False})` 中引用

```python
boot = noc.add_mode_flag("boot_mode", port="boot_sel", active_value=1)
# 然后在 mapping 中:
flow.add_mapping("region_a", base=0x0, size="64K", mode={boot: True})
flow.add_mapping("region_b", base=0x0, size="1G",  mode={boot: False})
```

### 5.4 Observer — 错误观察器

```python
obs = noc.add_observer(name, clock)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | (必填) | observer 名 |
| `clock` | ClockDomain | None | 时钟域 |

#### Observer dataclass 完整字段

```python
@dataclass
class Observer:
    name: str
    clock: ClockDomain = None
    watched_targets: list = []      # 监视的 target 名列表
    interrupt_port: str = ""        # 中断输出端口名
    debug_output: str = "None"      # 调试输出模式
    error_loggers: dict = {}        # 错误日志器配置
```

**PDD 生成**:
- specification 层: `<object kind="observer">` (含 clock, debugOutput, errorLoggers)
- architecture 层: 自动生成 `obsSwitch` + `observationRoute`
- structure 层: shadow (含 tacticalPorts → interrupt 端口映射)

**注意**: Observer 的完整配置 (watched_targets、interrupt_port) 需手动设置 dataclass 字段，`add_observer()` 返回对象后修改:

```python
obs = noc.add_observer("obs_0", clock=clk)
obs.watched_targets = ["targ_0", "targ_1"]
obs.interrupt_port = "irq_out"
```

---

## 6. Architecture API (自动拓扑与手动拓扑)

### 6.1 模块: `flexnoc_dsl.architecture` + `flexnoc_dsl.switch`

| 导出 | 类型 | 说明 |
|------|------|------|
| `Architecture` | class | 拓扑管理器 |
| `DtpSwitch` | dataclass | 数据通路交叉开关 |
| `DtpLink` | dataclass | CDC FIFO / 速率适配器链路 |
| `SrvSwitch` | dataclass | 服务路由开关 (NOC registers) |
| `ObsSwitch` | dataclass | 观察路由开关 (Observer) |
| `Route` | dataclass | 路由路径 (init flow → target flow) |

### 6.2 自动派生 (默认行为)

**无需任何手动操作**。`write_pdd()` 调用 `_finalize()` → `auto_derive()`，自动选择策略:

| 场景 | 策略 | 生成物 |
|------|------|--------|
| **单时钟域** | `_derive_single_clock()` | 2 个 dtpSwitch (sw000=rsp侧, sw001=req侧) |
| **多时钟域** | `_derive_multi_clock()` | 每域 2 个 switch + 跨域 FIFO dtpLink |
| **有 Observer** | `_derive_observation()` | obsSwitch + observationRoute |
| **有 NOC Registers** | `_derive_service()` | srvSwitch + serviceRoute |

#### 单时钟域自动拓扑

```
init_0 ──┐          ┌── targ_0
          ├─ sw000 ─ sw001 ─┤
init_1 ──┘          └── targ_1

sw000: response 侧 (domainCrossings = 所有 initiator 的 I 端口)
sw001: request 侧  (domainCrossings = 所有 target 的 T 端口)
所有路由: request 走 sw001, response 走 sw000
```

#### 多时钟域自动拓扑

```
domain_a (500MHz):           domain_b (200MHz):
init_0 ── sw000(rsp) ── sw001(req)  ──FIFO──  sw002(rsp) ── sw003(req) ── targ_0

每个时钟域: 1 pair (rsp_sw + req_sw)
跨域: 2 个 dtpLink (fifo_req_NNN + fifo_rsp_NNN)
```

自动生成的 dtpLink 参数:
- `buffering = "FIFO"`
- `n_byte = 32`
- `n_packet = 4`

### 6.3 手动拓扑 API

通过 `noc.architecture` 访问，**一旦调用手动 API 即切换为手动模式，跳过自动派生**。

#### `architecture.add_switch(name, clock, n_byte_per_word, header_penalty)`

| 参数 | 类型 | 默认值 | PDD 对应 |
|------|------|--------|---------|
| `name` | str | (必填) | dtpSwitch name |
| `clock` | ClockDomain | None | common/clock |
| `n_byte_per_word` | int | 8 | serialization/nBytePerWord |
| `header_penalty` | str | `"NONE"` | serialization/headerPenalty |

#### `architecture.add_link(name, clock, buffering, size, packets, n_byte_per_word)`

| 参数 | 类型 | 默认值 | PDD 对应 |
|------|------|--------|---------|
| `name` | str | (必填) | dtpLink name |
| `clock` | ClockDomain | None | common/clock |
| `buffering` | str | `"FIFO"` | datapath/buffering |
| `size` | int | 32 | buffering/nByte |
| `packets` | int | 4 | buffering/nPacket |
| `n_byte_per_word` | int | 8 | serialization/nBytePerWord |

#### `architecture.set_route(init_flow, targ_flow, request, response)`

```python
arch = noc.architecture
sw_a = arch.add_switch("sw_top", clock=clk)
sw_b = arch.add_switch("sw_mid", clock=clk)
fifo = arch.add_link("cdc_fifo", clock=clk_b, buffering="FIFO", size=64, packets=8)

arch.set_route(
    init_flow="init_0/I/0",
    targ_flow="targ_0/T/0",
    request=[sw_a, fifo, sw_b],     # 可传对象或字符串
    response=[sw_b, fifo, sw_a],
)
```

### 6.4 DtpSwitch 完整字段

```python
@dataclass
class DtpSwitch:
    name: str
    clock_ref: str = ""              # arch scope clock 引用
    domain_crossings: list = []      # 连接的 socket 端口列表
    n_byte_per_word: int = 8         # → serialization/nBytePerWord
    header_penalty: str = "NONE"     # → serialization/headerPenalty
```

### 6.5 DtpLink 完整字段

```python
@dataclass
class DtpLink:
    name: str
    clock_ref: str = ""
    buffering: str = "FIFO"          # "FIFO" or "RATE_ADAPTER"
    n_byte: int = 32                 # FIFO 深度 (字节)
    n_packet: int = 4                # FIFO 深度 (包)
    n_byte_per_word: int = 8
    header_penalty: str = "NONE"
    has_module: bool = True          # False = 虚拟链路 (不生成硬件)
```

### 6.6 Architecture Shadow (自动生成)

对每个 Initiator/Target，architecture 层自动生成 shadow 元素:
- Initiator shadow: `nPendingTrans` + `nPendingOrderId` (取自 `add_initiator()` 参数)
- Target shadow: `nPendingTrans` (取自 `add_target()` 参数)

---

## 7. NocProject API (顶层入口)

### 7.1 构造

```python
noc = NocProject(name: str)
```

自动派生 3 个层名:
- specification: `{name}` (如 `xbar_2x2`)
- architecture: `{name}_arch`
- structure: `{name}_struct`

### 7.2 完整方法列表

| 方法 | 返回 | 说明 | Feature |
|------|------|------|---------|
| `add_protocol(name, proto)` | Protocol | 注册协议 | 协议定义 |
| `add_clock(name, freq, ...)` | ClockDomain | 添加时钟域 | 时钟/多时钟 |
| `add_initiator(name, ...)` | Initiator | 添加发起方 | Socket |
| `add_target(name, ...)` | Target | 添加接收方 | Socket |
| `add_interleaved_targets(names, ...)` | list[Target] | 添加交织 target 组 | Interleave |
| `add_observer(name, clock)` | Observer | 添加错误观察器 | Observer |
| `add_mode_flag(name, port, ...)` | ModeFlag | 添加模式标志 | Remap |
| `add_user_port(name, ...)` | Port | 添加用户端口 | User Port |
| `add_noc_registers(name, clock, base)` | None | 添加 NOC 寄存器 | Service Route |
| `set_urgency_levels(levels)` | None | 设置 QoS 紧急级别 | QoS |
| `connect_all()` | None | 全连接 | Connectivity |
| `connect(init, targ_list)` | None | 选择性连接 | Connectivity |
| `disconnect(init, targ)` | None | 断开连接 | Connectivity |
| `set_export(fmt, simulator, name)` | None | 设置导出选项 | Export |
| `write_pdd(path)` | None | 生成 PDD 文件 | 输出 |
| `get_export_command(pdd, outdir)` | str | 生成 FlexNoC CLI 命令 | 工具 |
| `architecture` | Architecture | 架构层访问 (手动拓扑) | 拓扑 |

### 7.3 NOC Registers (Service Route)

```python
noc.add_noc_registers(name="noc_regs", clock=clk, base=0xFF000000)
```

**效果**: 自动生成 `srvSwitch` + `serviceRoute`，使外部可通过 APB/AXI 访问 NOC 内部寄存器。

### 7.4 QoS (Urgency Levels)

```python
noc.set_urgency_levels(4)  # 默认 2
```

**PDD 对应**: `specification/properties/globals/nUrgencyLevel`

控制路由仲裁的优先级级别数。值越大支持越细粒度的优先级区分。

### 7.5 Export 配置

```python
noc.set_export(fmt="Verilog", simulator="VCS", name="exports.Vlog")
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fmt` | str | `"Verilog"` | 导出格式 |
| `simulator` | str | `"VCS"` | 仿真器 |
| `name` | str | 自动 | exportOption 名 (默认 `exports.Vlog`) |

### 7.6 `_finalize()` 自动行为 (调用 `write_pdd` 时触发)

1. 为没有 flow 的 Initiator/Target 自动创建默认 flow + mapping
2. 如果没有设置 connectivity，自动 `connect_all()`
3. 自动调用 `architecture.auto_derive()` (除非手动模式)

---

## 8. 端到端工作流

```bash
# Step 1: 编写 Python 脚本 (my_noc.py)
python3 my_noc.py
# → 生成 my_noc.pdd

# Step 2: Docker 中运行 FlexNoC 导出 Verilog
docker run --rm --hostname YunqiLaptop --cap-add NET_ADMIN --entrypoint bash \
  -v ~/flexnoc-work:/work flexnoc:5.3.0-standalone -c '
ip link set eth0 down; ip link set eth0 name xp0
ip link set xp0 address 00:21:5a:45:ac:60; ip link set xp0 up
cd /opt/arteris/License && rm -f run/*.pid && bash arteris start 2>/dev/null && sleep 5
Xvfb :99 -screen 0 1024x768x24 & sleep 2; export DISPLAY=:99
source /opt/flexnoc/5.3.0/etc/bashrc
export LD_LIBRARY_PATH="/opt/flexnoc/5.3.0/TopologyEditor/lib:$LD_LIBRARY_PATH"
FlexNoC -d False -p /work/my_noc.pdd exportVerilog \
  -s my_noc_struct -c exports.Vlog -o /work/output
'
# → Verilog RTL 输出到 ~/flexnoc-work/output/
```

**关键**: 必须用 `-d False` 让 FlexNoC 自动填充 architecture/structure。

---

## 9. 已支持 Feature 矩阵

| Feature | API 入口 | 参数 | 验证状态 |
|---------|---------|------|---------|
| **AXI 协议** | `AXI(addr, data, id)` | wAddr, wData, wId, enRead/Write, useFixed | ✅ 端到端验证 |
| **APB 协议** | `APB(addr, data)` | wAddr, wData | ✅ PDD 生成 |
| **OCP 协议** | `OCP(addr, data, id)` | wAddr, wData, wId | ✅ PDD 生成 |
| **协议扩展字段** | `AXI(**kwargs)` | wReqUser, wRspUser 等 | ✅ PDD 生成 |
| **单时钟域** | `add_clock()` | freq, port, reset | ✅ 端到端验证 |
| **多时钟域** | 多次 `add_clock()` | 每域独立 freq | ✅ 自动 CDC FIFO |
| **频率解析** | freq 参数 | "500MHz", "1GHz", 266e6 | ✅ |
| **Gated Clock** | `clock_type="Gated"` | | ✅ PDD 生成 |
| **Initiator Socket** | `add_initiator()` | pending_trans, pending_ids, soft_lock | ✅ 端到端验证 |
| **Target Socket** | `add_target()` | base, size, pending_trans, seq_id_width | ✅ 端到端验证 |
| **全连接** | `connect_all()` | | ✅ 端到端验证 |
| **选择性连接** | `connect(init, targs)` | | ✅ PDD 生成 |
| **断开连接** | `disconnect(init, targ)` | | ✅ PDD 生成 |
| **多 Flow** | `init.flow(idx)` | 每 flow 独立 mapping | ✅ PDD 生成 |
| **多 Mapping** | `flow.add_mapping()` | base, size, local_address | ✅ PDD 生成 |
| **地址 Remap** | `add_mode_flag()` + mapping modes | active_value, mode 条件 | ✅ PDD 生成 |
| **QoS (Urgency)** | `set_urgency_levels(n)` | nUrgencyLevel | ✅ PDD 生成 |
| **User Port** | `add_user_port()` | direction, width, default | ✅ PDD 生成 |
| **Observer** | `add_observer()` | watched_targets, interrupt_port | ✅ PDD 生成 |
| **NOC Registers** | `add_noc_registers()` | name, clock, base | ✅ PDD 生成 |
| **自动拓扑** | 自动 `auto_derive()` | 单/多时钟自适应 | ✅ 端到端验证 |
| **手动拓扑** | `architecture.add_switch/link/set_route` | 完全自定义 switch/link/route | ✅ PDD 生成 |
| **CDC FIFO Link** | 多时钟自动 / `add_link(buffering="FIFO")` | nByte, nPacket | ✅ PDD 生成 |
| **AXI userMapping** | 自动 (AXI Target) | ARCache, AWCache, Prot → CONST_0 | ✅ 端到端验证 |
| **TestMode 端口** | 自动生成 | clock="None", 每时钟域共享 | ✅ 端到端验证 |
| **Verilog 导出** | `set_export("Verilog")` | simulator="VCS" | ✅ 端到端验证 |
| **Export 命令生成** | `get_export_command()` | pdd_path, output_dir | ✅ |
| **地址交织 (Interleave)** | `add_interleaved_targets()` | stripe_size, total_size, mask 自动计算 | ✅ 端到端验证 |
| **响应交织** | `min_interleave_size` 参数 | initiator/target 的 minInterleaveSize | ✅ PDD 生成 |

---

## 10. 已知不支持 Feature

| Feature | FlexNoC 支持 | DSL 状态 | 说明 |
|---------|-------------|---------|------|
| **Firewall** | ✅ | ❌ 未实现 | 需要 firewall 对象 + security zone 配置 |
| **AXI4/AXI5/ACE/CHI** | ✅ | ❌ 未实现 | 仅支持 AXI (V3 级别)，不支持 AXI4-Stream/ACE/CHI |
| **AHB 协议** | ✅ | ❌ 未实现 | 需要新的工厂函数 |
| **NSP/SFI/LLI 协议** | ✅ | ❌ 未实现 | 特殊 link-layer 协议 |
| **FlexWay/FlexGen** | ✅ | ❌ 未实现 | 高级互连模式 |
| **Power Domain** | ✅ | ⚠️ 部分 | ClockDomain 含 clock/reset，但无独立 power/activityZone 定义 |
| **Voltage Domain** | ✅ | ❌ 未实现 | 需要 voltage 对象 |
| **UserFlag** | ✅ | ❌ 未实现 | 用户自定义标志 (privileged, secure, debug 等) |
| **自定义 userMapping** | ✅ | ⚠️ 部分 | AXI Target 自动生成固定值，不支持自定义映射规则 |
| **Scenario** | ✅ | ❌ 未实现 | 场景定义 (性能分析) |
| **Queue** | ✅ | ❌ 未实现 | 队列配置 (性能调优) |
| **TargetModel** | ✅ | ❌ 未实现 | 目标模型 (仿真用) |
| **swModule** | ✅ | ❌ 未实现 | 子模块嵌套 (NoC 内嵌 NoC) |
| **Pipe 配置** | ✅ | ❌ 未实现 | switch 的 inputPipes/outputPipes (空生成) |
| **RATE_ADAPTER link** | ✅ | ⚠️ API 预留 | `buffering="RATE_ADAPTER"` 参数存在但未验证 |
| **多 exportOption** | ✅ | ⚠️ 单个 | 仅支持 1 个 export 配置 (VCS Verilog) |
| **SystemC 导出** | ✅ | ❌ 未实现 | `set_export("SystemC")` 理论可用但未验证 |
| **IP-XACT 导出** | ✅ | ❌ 未实现 | 需要 register model |
| **仲裁策略自定义** | ✅ | ⚠️ 固定 | 硬编码为 ROTATE，不支持 PRIORITY/LRU 等 |
| **Observer 完整配置** | ✅ | ⚠️ 基础 | 仅 clock + watched_targets，不支持高级过滤/统计 |

### 扩展建议

优先级最高的待实现 feature:
1. **Firewall** — 安全域隔离，SoC 设计必需
2. **UserFlag** — AXI secure/privileged 信号映射
3. **多 exportOption** — 同时生成 VCS/DC/SystemC
4. **自定义仲裁** — PRIORITY 策略用于 QoS 差异化
