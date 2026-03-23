# Architecture API (自动拓扑与手动拓扑)

> 模块: `flexnoc_dsl.architecture` + `flexnoc_dsl.switch`
> 职责: 管理 NoC 的数据通路拓扑（switch、link、route），支持自动派生和手动配置

---

## 1. 概述

Architecture 层定义 NoC 的物理拓扑结构。**默认完全自动派生**，用户无需关心。
仅在需要自定义拓扑时使用手动 API。

**两种模式**:

| 模式 | 触发条件 | 说明 |
|------|---------|------|
| **自动** (默认) | 不调用任何 `architecture.add_*` 方法 | `write_pdd()` 时自动计算 |
| **手动** | 调用 `architecture.add_switch()` 或 `add_link()` | 跳过自动派生 |

## 2. 数据类型

### 2.1 DtpSwitch — 数据通路交叉开关

```python
@dataclass
class DtpSwitch:
    name: str                        # switch 名 (如 "dtpSwitch000")
    clock_ref: str = ""              # architecture 层时钟引用
    domain_crossings: list = []      # 连接的 socket 端口列表
    n_byte_per_word: int = 8         # → serialization/nBytePerWord
    header_penalty: str = "NONE"     # → serialization/headerPenalty
    input_pipes: dict = {}           # {crossing_ref: stages} → inputPipes
    output_pipes: dict = {}          # {crossing_ref: stages} → outputPipes
```

| PDD key | 类型 | 说明 |
|---------|------|------|
| `nBytePerWord` | int | 每字字节数，通常 = max(data_width) / 8 |
| `headerPenalty` | str | `"NONE"`, `"AUTO"`, 或自定义值 |
| `inputPipes` | dict | 输入流水线级数 |
| `outputPipes` | dict | 输出流水线级数 |

### 2.2 DtpLink — CDC FIFO / 速率适配器

```python
@dataclass
class DtpLink:
    name: str
    clock_ref: str = ""
    buffering: str = "FIFO"     # "FIFO" 或 "RATE_ADAPTER"
    n_byte: int = 32            # FIFO 深度 (字节)
    n_packet: int = 4           # FIFO 深度 (包)
    n_byte_per_word: int = 8
    header_penalty: str = "NONE"
    has_module: bool = True     # False = 虚拟链路 (不生成硬件)
```

### 2.3 SrvSwitch — 服务路由开关

```python
@dataclass
class SrvSwitch:
    name: str
    clock_ref: str = ""
    domain_crossings: list = []
    n_byte_per_word: int = 1
    header_penalty: str = "AUTO"
```

用于 NOC 寄存器访问路径。

### 2.4 ObsSwitch — 观察路由开关

```python
@dataclass
class ObsSwitch:
    name: str
    clock_ref: str = ""
    domain_crossings: list = []
    n_byte_per_word: int = 0
    header_penalty: str = "AUTO"
```

用于 Observer 错误报告路径。

### 2.5 Route — 路由路径

```python
@dataclass
class Route:
    init_ref: str        # "init_0/I/0" (socket/role/flow)
    targ_ref: str        # "targ_0/T/0"
    request_path: list   # switch/link 名列表
    response_path: list  # switch/link 名列表
```

## 3. 自动派生策略

### 3.1 单时钟域

```
init_0 ──┐              ┌── targ_0
          ├── sw000 ── sw001 ──┤
init_1 ──┘              └── targ_1

sw000: response 侧 (domainCrossings = 所有 initiator/I)
sw001: request 侧  (domainCrossings = 所有 target/T)
所有路由: request → sw001, response → sw000
```

生成: 2 个 DtpSwitch

### 3.2 多时钟域

```
domain_a:  sw000(rsp) ── sw001(req)
                    │            │
              fifo_rsp_000  fifo_req_000
                    │            │
domain_b:  sw002(rsp) ── sw003(req)
```

生成: 每域 2 个 DtpSwitch + 每跨域 2 个 DtpLink (fifo_req + fifo_rsp)

**自动计算**:
- `n_byte_per_word` = max(所有 socket 的 data_width) / 8
- DtpLink: `buffering="FIFO"`, `n_byte=32`, `n_packet=4`

### 3.3 有 Observer

自动生成:
- 1 个 `ObsSwitch`
- 每个 target-observer 对的 `observationRoute`

### 3.4 有 NOC Registers

自动生成:
- 1 个 `SrvSwitch`
- `serviceRoute` 到各 target

## 4. 手动拓扑 API

通过 `noc.architecture` 访问:

### 4.1 `architecture.add_switch()`

```python
sw = noc.architecture.add_switch(name, clock, n_byte_per_word, header_penalty)
```

| 参数 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|---------|------|
| `name` | str | *必填* | 合法标识符 | switch 名 |
| `clock` | ClockDomain | None | 已创建 ClockDomain | 时钟域 |
| `n_byte_per_word` | int | 8 | 1, 2, 4, 8, 16, ... | 每字字节数 |
| `header_penalty` | str | `"NONE"` | `"NONE"`, `"AUTO"` | header 代价 |

**返回**: `DtpSwitch` 对象

**Pipeline 配置** (在返回对象上设置):
```python
sw = noc.architecture.add_switch("sw0", clock=clk)
sw.input_pipes = {"(switchBasedArchitecture:init_0/I)": 1}   # 1 级输入流水线
sw.output_pipes = {"(switchBasedArchitecture:targ_0/T)": 2}  # 2 级输出流水线
```

### 4.2 `architecture.add_link()`

```python
link = noc.architecture.add_link(name, clock, buffering, size, packets, n_byte_per_word)
```

| 参数 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|---------|------|
| `name` | str | *必填* | 合法标识符 | link 名 |
| `clock` | ClockDomain | None | 已创建 ClockDomain | 时钟域 |
| `buffering` | str | `"FIFO"` | `"FIFO"`, `"RATE_ADAPTER"` | 缓冲类型 |
| `size` | int | 32 | ≥ 1 | FIFO 字节深度 |
| `packets` | int | 4 | ≥ 1 | FIFO 包深度 |
| `n_byte_per_word` | int | 8 | 1, 2, 4, 8, ... | 每字字节数 |

**返回**: `DtpLink` 对象

### 4.3 `architecture.set_route()`

```python
noc.architecture.set_route(init_flow, targ_flow, request, response)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `init_flow` | str | 发起方 flow 路径: `"init_0/I/0"` |
| `targ_flow` | str | 接收方 flow 路径: `"targ_0/T/0"` |
| `request` | list | request 路径的 switch/link 列表 (对象或名称字符串) |
| `response` | list | response 路径的 switch/link 列表 |

**示例**:
```python
arch = noc.architecture
sw_a = arch.add_switch("sw_top", clock=clk)
sw_b = arch.add_switch("sw_mid", clock=clk)
fifo = arch.add_link("cdc_fifo", clock=clk_b)

arch.set_route(
    init_flow="init_0/I/0",
    targ_flow="targ_0/T/0",
    request=[sw_a, fifo, sw_b],
    response=[sw_b, fifo, sw_a],
)
```

## 5. 仲裁策略

```python
noc.set_arbiter_mode(mode)
```

| 参数 | 取值 | 说明 |
|------|------|------|
| `mode` | `"FIXED"` | 固定优先级仲裁 |
| | `"ROTATE"` | 旋转优先级 (默认) |
| | `"ROUND_ROBIN"` | 轮询仲裁 |
| | `"FIFO"` | 先进先出仲裁 |
| | `"ROUND_ROBIN_URG"` | 带紧急级别的轮询 |

**PDD 位置**: architecture → globals/muxDefaultArbiters (对 2/3/4 ports 统一设置)

## 6. QoS 参数

### 6.1 urgencyLevel

```python
noc.set_urgency_levels(levels)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key |
|------|------|--------|---------|---------|
| `levels` | int | 2 | 1–8 | specification/globals/nUrgencyLevel |

### 6.2 useErrorCodes

```python
noc.set_use_error_codes(enabled=True)
```

| 参数 | 类型 | 默认值 | PDD key |
|------|------|--------|---------|
| `enabled` | bool | True | specification/globals/useErrorCodes |

## 7. Architecture Shadow

自动生成的 shadow 元素:

| 层 | Socket 类型 | 生成字段 |
|----|-----------|---------|
| architecture | Initiator/I | `nPendingTrans`, `nPendingOrderId`, (`nReassemblyBuffer`) |
| architecture | Target/T | `nPendingTrans`, (`seqIdAllocation`) |
| structure | 所有 | tacticalPorts (如 Press), 流空 shadow |

## 8. 冲突与约束

| 场景 | 约束 | 后果 |
|------|------|------|
| 手动模式 + auto_derive | ❌ 自动跳过 | 手动 switch/link/route 生效 |
| arbiter_mode 无效值 | ⚠️ 未校验 | FlexNoC 可能报错 |
| pipeline stages 引用错误路径 | ⚠️ 无效 | switch 可能忽略 |
| RATE_ADAPTER buffering | ⚠️ 未验证 | API 预留但未 E2E 验证 |
