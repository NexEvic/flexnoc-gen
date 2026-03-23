# Socket API (Initiator / Target / Flow / Mapping)

> 模块: `flexnoc_dsl.socket`
> 职责: 定义 NoC 的发起方(Initiator)和接收方(Target) socket，数据流(Flow)，地址映射(Mapping)，地址交织

---

## 1. 概述

Socket 是 NoC 的核心概念，代表 IP 与 NoC 的接口点。每个 socket 包含:
- 协议引用: 使用哪种总线协议
- 时钟引用: 属于哪个时钟域
- 数据流/地址映射: Initiator 的寻址规则

```python
init = noc.add_initiator("cpu", protocol=axi, clock=clk)
targ = noc.add_target("mem", protocol=axi, clock=clk, base=0x0, size="256M")
```

## 2. Initiator — 发起方 Socket

### 2.1 创建: `noc.add_initiator()`

```python
init = noc.add_initiator(name, protocol, clock, pending_trans, pending_ids,
                         use_soft_lock, use_press, clock_gating, comment,
                         power_domain, conversion)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD 位置 | 说明 |
|------|------|--------|---------|---------|------|
| `name` | str | *必填* | 合法标识符 | socket name | 接口名，全项目唯一 |
| `protocol` | Protocol | None | 已注册的 Protocol | properties/protocol/reference | 协议对象 |
| `clock` | ClockDomain | None | 已创建的 ClockDomain | properties/clock | 时钟域 |
| `pending_trans` | int | 4 | 1–256 | arch shadow: nPendingTrans | 最大未完成事务数 |
| `pending_ids` | int | 1 | 1–256 | arch shadow: nPendingOrderId | 最大并发排序 ID 数 |
| `use_soft_lock` | bool | False | True/False | parameters/useSoftLock | 启用软锁 |
| `use_press` | bool | False | True/False | parameters/usePress | 启用 QoS 压力信号 |
| `clock_gating` | str | `""` | `""`, `"#Common"`, 自定义 | properties/clockGating | 时钟门控模式 |
| `comment` | str | `""` | 任意字符串 | properties/comment | 设计者注释 |
| `power_domain` | str | `""` | 已注册的 PowerDomain 名 | properties/power/IPpowerDomain | 电源域引用 |
| `conversion` | dict | `{}` | key-value 对 | properties/conversion | 协议转换配置 |

**返回**: `Initiator` 对象

### 2.2 参数详解

#### pending_trans / pending_ids

控制 NIU (Network Interface Unit) 的事务缓冲能力:
- `pending_trans`: 发起方可以同时发出的最大未完成事务数。值越大，带宽利用率越高，但面积开销越大。
- `pending_ids`: 用于 AXI 乱序完成的排序 ID 数。`1` = 严格顺序，`>1` = 支持乱序。

**PDD 位置**: architecture shadow → `datapath/performance/nPendingTrans` 和 `nPendingOrderId`

#### use_press

启用 QoS 压力信号 (Press)。当 `use_press=True` 时，**自动生成**:
1. **specification 层**: `press` 端口 (`User/Input`, width = `nUrgencyLevel`, defaultVal = 0)
2. **architecture 层**: `press` shadow
3. **structure 层**: `press` shadow + `tacticalPorts/main/Press` 映射

**约束**: `use_press` 仅对 Initiator 有效，Target 不支持。

#### clock_gating

| 值 | 含义 | PDD 输出 |
|----|------|---------|
| `""` (空) | 不输出 clockGating | 无 |
| `"#Common"` | 使用公共门控时钟 | `<entry key="clockGating" value="#Common"/>` |
| 自定义值 | 使用指定门控 | `<entry key="clockGating" value="自定义值"/>` |

#### conversion

协议转换配置。空 dict `{}` 在 PDD 中生成空的 `<entry key="conversion"/>`。
有值时生成子条目:

```python
init = noc.add_initiator("cpu", protocol=axi, clock=clk,
                         conversion={"someKey": "someValue"})
# → <entry key="conversion"><entry key="someKey" value="someValue"/></entry>
```

#### 混合协议自动行为

当 AXI Initiator 连接到 AHB 或 APB Target 时，architecture shadow 自动添加 `nReassemblyBuffer=2`。
无需手动配置。

### 2.3 Initiator 数据流 (Flow)

```python
flow0 = init.flow(0)   # 获取 flow "0"（不存在时自动创建）
flow1 = init.flow(1)   # 获取 flow "1"
```

**自动行为**: 如果用户没有手动创建 flow，`_finalize()` 时自动创建 flow "0"，
mapping "0" 的 mask 覆盖所有连接 target 的地址空间并集。

## 3. Target — 接收方 Socket

### 3.1 创建: `noc.add_target()`

```python
targ = noc.add_target(name, protocol, clock, base, size, pending_trans,
                      seq_id_width, use_soft_lock, clock_gating, comment,
                      power_domain, seq_id_allocation, conversion,
                      specials_mapping)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD 位置 | 说明 |
|------|------|--------|---------|---------|------|
| `name` | str | *必填* | 合法标识符 | socket name | 接口名 |
| `protocol` | Protocol | None | 已注册 Protocol | properties/protocol/reference | 协议 |
| `clock` | ClockDomain | None | 已创建 ClockDomain | properties/clock | 时钟域 |
| `base` | int | 0 | 0 – 2^64-1 | mapping/globalAddress | 基地址 |
| `size` | str/int | `"0"` | 正整数，支持后缀 | 计算 mapping/mask | 地址空间大小 |
| `pending_trans` | int | 16 | 1–256 (AHB: 最大1) | arch shadow: nPendingTrans | 未完成事务数 |
| `seq_id_width` | int | 0 | 0–32 (0=用协议 id_width) | parameters/wSeqId | 序列 ID 宽度 |
| `use_soft_lock` | bool | False | True/False | parameters/useSoftLock | 软锁 |
| `clock_gating` | str | `""` | `""`, `"#Common"`, 自定义 | properties/clockGating | 门控 |
| `comment` | str | `""` | 任意字符串 | properties/comment | 注释 |
| `power_domain` | str | `""` | 已注册 PowerDomain 名 | properties/power/IPpowerDomain | 电源域 |
| `seq_id_allocation` | str | `""` | `""`, `"DYNAMIC"`, `"STATIC"` | arch shadow: seqIdAllocation | ID 分配策略 |
| `conversion` | dict | `{}` | key-value | properties/conversion | 协议转换 |
| `specials_mapping` | dict | `{}` | 见下文 | userMapping specials | 自定义 specials |

**返回**: `Target` 对象

### 3.2 Size 解析

`size` 参数支持多种格式:

| 输入 | 解析结果 (bytes) | 说明 |
|------|-----------------|------|
| `"256M"` | 268,435,456 | 256 × 1024² |
| `"1G"` | 1,073,741,824 | 1 × 1024³ |
| `"4K"` | 4,096 | 4 × 1024 |
| `"1T"` | 1,099,511,627,776 | 1 × 1024⁴ |
| `"0x1000"` | 4,096 | 十六进制 |
| `65536` | 65,536 | 直接整数 |

后缀: `K` (1024), `M` (1M), `G` (1G), `T` (1T)

### 3.3 seq_id_allocation

控制 target NIU 的 sequence ID 分配策略:

| 值 | PDD 输出 | 行为 |
|----|---------|------|
| `""` (空) | 不输出 | FlexNoC 使用默认策略 |
| `"DYNAMIC"` | `seqIdAllocation=DYNAMIC` | 动态分配 ID，提高利用率 |
| `"STATIC"` | `seqIdAllocation=STATIC` | 静态分配 ID，确定性更强 |

**PDD 位置**: architecture shadow → `datapath/performance/seqIdAllocation`
（注意: 是在 architecture shadow 中，**不是** specification parameters 中）

### 3.4 AXI Target 自动 userMapping

当协议类型为 AXI 时，Target 自动生成 userMapping:

**默认行为** (无 UserFlag 时):
```xml
<entry key="userMapping">
  <entry key="ARCache"><entry key="specials"><entry key="CONST_0" value="#0,1,2,3"/></entry></entry>
  <entry key="AWCache"><entry key="specials"><entry key="CONST_0" value="#0,1,2,3"/></entry></entry>
  <entry key="Prot"><entry key="specials"><entry key="CONST_0" value="#0,1,2"/></entry></entry>
</entry>
```

**有 UserFlag 时**: 使用 `target.user_mapping` dict 映射信号到 userFlag。

**自定义 specials (specials_mapping)**: 覆盖默认 CONST_0:
```python
targ = noc.add_target("mem", protocol=axi, clock=clk, base=0, size="256M",
                      specials_mapping={
                          "ARCache": {"CONST_1": "#0,1,2,3"},
                          "AWCache": {"CONST_1": "#0,1,2,3"},
                          "Prot": {"CONST_1": "#0,1,2"},
                      })
```

### 3.5 AHB Target 自动 userMapping

AHB target 自动生成:
```xml
<entry key="HProt"><entry key="specials"><entry key="CONST_0" value="#0,1,2,3"/></entry></entry>
<entry key="XorHProt_6"><entry key="specials"><entry key="CONST_0" value="#0"/></entry></entry>
```

### 3.6 自动 Flow 行为

Target 的自动 flow 生成:
- flow "0", mapping "0"
- `globalAddress = base_address`
- `mask = size - 1`

## 4. Flow — 数据流

### 4.1 Flow dataclass

```python
@dataclass
class Flow:
    name: str = "0"                    # flow 名
    mappings: list[Mapping] = []       # 地址映射列表
    default_error_target: str = ""     # 默认错误 target (PDD: defaultErrorTarget)
```

### 4.2 访问/创建 Flow

```python
flow0 = init.flow(0)   # 获取或创建 flow "0"
flow1 = init.flow(1)   # 获取或创建 flow "1"
```

`flow(idx)` 自动按需创建中间 flow（如调用 `flow(2)` 会创建 flow "0", "1", "2"）。

### 4.3 添加 Mapping

```python
mapping = flow.add_mapping(name, base, size, local_address, access, mode, comment)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `name` | str | `""` (自增) | 合法标识符 | mapping name | 空时用序号 |
| `base` | int | 0 | 0 – 2^64-1 | `globalAddress` | 全局基地址 |
| `size` | str/int | 0 | 正整数，支持后缀 | 计算 `mask` | 大小 |
| `local_address` | int | 0 | 0 – 2^64-1 | `localAddress` | 本地基地址 |
| `access` | str | `"ReadWrite"` | `"ReadWrite"`, `"Read"`, `"Write"`, `"None"` | `access` | 访问类型 |
| `mode` | dict | None | `{ModeFlag: bool}` | `modes` 条目 | Remap 模式条件 |
| `comment` | str | `""` | 任意字符串 | `comment` | 注释 |

**返回**: `Mapping` 对象

## 5. Mapping dataclass

```python
@dataclass
class Mapping:
    name: str
    global_address: int = 0       # → PDD globalAddress (十进制)
    local_address: int = 0        # → PDD localAddress
    mask: int = 0                 # → PDD mask（显式优先）
    size: int = 0                 # → 自动转 mask (mask = size - 1)
    access: str = "ReadWrite"     # → PDD access (仅非 ReadWrite 时输出)
    modes: dict = {}              # → PDD modes 条目
    comment: str = ""             # → PDD comment
```

**Mask 计算**: `effective_mask()` 返回:
- `mask` 值（如果显式设置）
- `size - 1`（如果由 size 推导）

**PDD 附加输出**: 每个 mapping 自动生成空的 `readPermissions` 和 `writePermissions` 条目。

## 6. Remap (Mode-based Mapping)

通过 ModeFlag 控制映射选择:

```python
boot = noc.add_mode_flag("boot_mode", port="boot_sel", active_value=1)

init = noc.add_initiator("cpu", protocol=axi, clock=clk)
flow0 = init.flow(0)

# boot_mode=True 时访问 ROM
flow0.add_mapping("rom", base=0x0, size="64K", mode={boot: True})
# boot_mode=False 时访问 DRAM
flow0.add_mapping("dram", base=0x0, size="256M", mode={boot: False})
```

## 7. 地址交织 (Address Interleaving)

### 7.1 高级 API: `noc.add_interleaved_targets()`

```python
targets = noc.add_interleaved_targets(names, protocol, clock,
    total_base, total_size, stripe_size, pending_trans, seq_id_width,
    use_soft_lock, min_interleave_size, access)
```

| 参数 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|---------|------|
| `names` | list[str] | *必填* | 长度为 2 的幂 | target 名列表 |
| `protocol` | Protocol | None | 已注册 Protocol | 共享协议 |
| `clock` | ClockDomain | None | 已创建 ClockDomain | 共享时钟域 |
| `total_base` | int | 0 | ≥ 0 | 交织区域起始地址 |
| `total_size` | str/int | `"0"` | 正整数 | 总大小 |
| `stripe_size` | str/int | `"4K"` | 2 的幂 | 交织粒度 |
| `pending_trans` | int | 16 | 1–256 | 每 target 未完成事务数 |
| `seq_id_width` | int | 0 | 0–32 | wSeqId |
| `use_soft_lock` | bool | False | True/False | 软锁 |
| `min_interleave_size` | int | -1 | -1, 0, 或正整数 | 响应交织大小 |
| `access` | str | `"ReadWrite"` | 见 Mapping access | 访问类型 |

**返回**: `list[Target]`

**约束**:
- `len(names)` 必须是 2 的幂（2, 4, 8, ...）
- `stripe_size` 必须是 2 的幂
- `total_size` 必须能被 `len(names)` 整除

### 7.2 交织原理

FlexNoC 通过 mask 中的 0 bit 选择 target:

```
stripe_size=1K, 2-way:
  mask = 0x7FFF_FBFF (bit 10 = 0)
  DDR0: globalAddress=0x000 (bit10=0)
  DDR1: globalAddress=0x400 (bit10=1)
```

### 7.3 min_interleave_size (响应交织)

| 值 | 含义 |
|----|------|
| -1 (默认) | 不输出参数 (FlexNoC 默认) |
| 0 | 禁用读响应交织 |
| wData/8 | 字级交织 (如 64-bit 时为 8) |
| N × wData/8 | N 字后才允许交织 |

Initiator 和 Target 均可设置:
```python
noc.add_initiator("cpu", protocol=axi, clock=clk, min_interleave_size=0)
noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1M",
               min_interleave_size=8)
```

**PDD 位置**: specification → parameters/minInterleaveSize

### 7.4 低级 API

```python
from flexnoc_dsl import compute_interleave_mask, create_interleaved_mappings

# 计算单个交织 mask
mask = compute_interleave_mask(
    per_target_size=1 << 30,  # 1GB per target
    stripe_size=1024,          # 1KB stripe
    num_targets=2,             # 2-way interleave
)

# 生成完整 mapping 列表
all_mappings = create_interleaved_mappings(
    num_targets=2,
    stripe_size=1024,
    total_size=2 << 30,
    base_address=0,
)
# all_mappings[0] → DDR0 的 [Mapping(...)]
# all_mappings[1] → DDR1 的 [Mapping(...)]
```

## 8. Connectivity — 连接矩阵

```python
noc.connect_all()                           # 全连接
noc.connect("init_0", ["targ_0", "targ_1"]) # 选择性连接
noc.disconnect("init_0", "targ_1")          # 断开连接
```

| 方法 | 说明 | PDD 对应 |
|------|------|---------|
| `connect_all()` | 所有 init → 所有 target | connectivity 全 True |
| `connect(init, targs)` | 指定 init → 指定 targets | 对应条目 True |
| `disconnect(init, targ)` | 断开特定连接 | 对应条目 False |

**⚠️ 自动行为**: 如果 `write_pdd()` 前没有调用任何 connect，自动执行 `connect_all()`。

## 9. UserMapping — 用户信号映射

### 9.1 默认 (CONST_0) 映射

AXI target 自动生成 `ARCache/AWCache → CONST_0 #0,1,2,3`, `Prot → CONST_0 #0,1,2`。

### 9.2 UserFlag 驱动的映射

```python
# 1. 定义 UserFlag
uf_secure = noc.add_user_flag("2_secureN")
uf_priv = noc.add_user_flag("1_privileged")

# 2. Initiator 驱动 UserFlag
init.user_mapping = {
    "userFlags": {
        "2_secureN": "CONST_0",
        "1_privileged": "CONST_0",
    }
}

# 3. Target 接收 UserFlag 映射
targ.user_mapping = {
    "ARCache": {"2_secureN": 0, "1_privileged": 1},
    "AWCache": {"2_secureN": 0, "1_privileged": 1},
    "Prot": {"1_privileged": 0, "2_secureN": 1},
}
```

### 9.3 自定义 Specials 映射 (specials_mapping)

覆盖默认 CONST_0 常量:

```python
targ = noc.add_target("mem", protocol=axi, clock=clk, base=0, size="256M",
                      specials_mapping={
                          "ARCache": {"CONST_1": "#0,1,2,3"},
                          "Prot": {"CONST_0": "#0", "CONST_1": "#1,2"},
                      })
```

**约束**: `specials_mapping` 仅在**无 UserFlag** 时生效。有 UserFlag 时使用 `user_mapping` 代替。

## 10. 冲突与约束汇总

| 场景 | 约束 | 后果 |
|------|------|------|
| AHB target pending_trans > 1 | ❌ 禁止 | FlexNoC 报错 |
| specials_mapping + UserFlag | ⚠️ 忽略 specials | UserFlag 映射优先 |
| min_interleave_size < 0 且非 -1 | ⚠️ 未定义 | 建议只用 -1 或 ≥ 0 |
| 交织 target 数非 2 的幂 | ❌ 禁止 | mask 计算错误 |
| base 未对齐 size | ⚠️ 可能 | FlexNoC 可能报地址冲突 |
| seq_id_allocation 在非 target 上设置 | — | 无效果 |
