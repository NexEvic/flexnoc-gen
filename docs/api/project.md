# NocProject API

> 模块: `flexnoc_dsl.project.NocProject`
> 职责: NoC 设计的顶层入口，管理所有组件的创建、连接和输出

---

## 1. 概述

`NocProject` 是 flexnoc_dsl 的核心类，提供完整的 NoC 设计 API。
所有设计操作都通过此类完成。

```python
from flexnoc_dsl import NocProject, AXI

noc = NocProject("my_noc")
```

## 2. 构造函数

```python
NocProject(name: str)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | str | 项目名。自动派生 spec/arch/struct 名 |

**自动派生命名**:
| 属性 | 值 | 用途 |
|------|-----|------|
| `_spec_name` | `name` | 规格名 |
| `_arch_name` | `f"{name}_arch"` | 架构名 |
| `_struct_name` | `f"{name}_struct"` | 结构名 |

## 3. 完整方法一览

### 3.1 协议管理

| 方法 | 签名 | 返回 | 说明 | 详细文档 |
|------|------|------|------|---------|
| `add_protocol` | `(name, proto)` | Protocol | 注册协议 | [protocol.md](protocol.md) |

### 3.2 时钟管理

| 方法 | 签名 | 返回 | 说明 | 详细文档 |
|------|------|------|------|---------|
| `add_clock` | `(name, freq, port, reset, test_mode, clock_type, voltage_ref, comment, power_ref)` | ClockDomain | 添加时钟域 | [clock.md](clock.md) |

**参数速查**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | *必填* | 时钟域名 |
| `freq` | str/int | `"500MHz"` | 频率 |
| `port` | str | `"clk"` | 时钟端口名 |
| `reset` | str | `"rst_n"` | 复位端口名 |
| `test_mode` | str | `"Tm"` | 测试模式端口 |
| `clock_type` | str | `"Root"` | `"Root"` 或 `"Gated"` |
| `voltage_ref` | str | `""` | 关联电压对象名 |
| `comment` | str | `""` | 注释 |
| `power_ref` | str | `""` | 关联 PowerDomain 名 |

### 3.3 Socket 管理

| 方法 | 签名 | 返回 | 说明 | 详细文档 |
|------|------|------|------|---------|
| `add_initiator` | `(name, protocol, clock, ...)` | Initiator | 添加发起端 | [socket.md](socket.md) |
| `add_target` | `(name, protocol, clock, ...)` | Target | 添加目标端 | [socket.md](socket.md) |
| `add_interleaved_targets` | `(names, protocol, clock, ...)` | list[Target] | 交织目标组 | [socket.md](socket.md) |

### 3.4 观察者

| 方法 | 签名 | 返回 | 说明 |
|------|------|------|------|
| `add_observer` | `(name, clock)` | Observer | 添加观察者端口 |

### 3.5 标志

| 方法 | 签名 | 返回 | 说明 | 详细文档 |
|------|------|------|------|---------|
| `add_mode_flag` | `(name, port, active_value)` | ModeFlag | 添加模式标志 | [port.md](port.md) |
| `add_user_flag` | `(name)` | UserFlag | 添加用户标志 | [port.md](port.md) |

### 3.6 电源

| 方法 | 签名 | 返回 | 说明 | 详细文档 |
|------|------|------|------|---------|
| `add_power_domain` | `(name, kind, comment, activity_zones)` | PowerDomain | 添加电源域 | [power.md](power.md) |
| `add_voltage` | `(name, value, comment)` | Voltage | 添加电压对象 | [power.md](power.md) |

### 3.7 用户端口

| 方法 | 签名 | 返回 | 说明 | 详细文档 |
|------|------|------|------|---------|
| `add_user_port` | `(name, direction, width, clock, default)` | Port | 添加用户自定义端口 | [port.md](port.md) |

**参数**:
| 参数 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|---------|------|
| `name` | str | *必填* | 合法标识符 | 端口名 |
| `direction` | str | `"Input"` | `"Input"`, `"Output"` | 方向 |
| `width` | int | `1` | ≥1 | 位宽 |
| `clock` | ClockDomain | `None` | 已注册时钟 | 关联时钟 |
| `default` | int | `None` | 整数值 | 默认值 (None=不设置) |

### 3.8 NOC 寄存器

| 方法 | 签名 | 返回 | 说明 |
|------|------|------|------|
| `add_noc_registers` | `(name, clock, base)` | None | 添加 NOC 管理寄存器接口 |

**参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | *必填* | 寄存器接口名 |
| `clock` | ClockDomain | `None` | 关联时钟 |
| `base` | int | `0` | 基地址 |

### 3.9 QoS (服务质量)

| 方法 | 签名 | 说明 |
|------|------|------|
| `set_urgency_levels` | `(levels: int)` | 设置紧急度级别数 (默认 2) |
| `set_arbiter_mode` | `(mode: str)` | 设置仲裁模式 |
| `set_use_error_codes` | `(enabled: bool)` | 启用错误码 |

**arbiter_mode 取值**:
| 值 | 说明 |
|----|------|
| `"FIXED"` | 固定优先级 |
| `"ROTATE"` | 旋转优先级 (默认) |
| `"ROUND_ROBIN"` | 轮询 |
| `"FIFO"` | 先进先出 |
| `"ROUND_ROBIN_URG"` | 紧急度感知轮询 |

### 3.10 连接

| 方法 | 签名 | 说明 |
|------|------|------|
| `connect_all()` | 无参 | 全网格连接 (所有 init → 所有 targ) |
| `connect` | `(init_name, targ_names)` | 指定 initiator 连接指定 targets |
| `disconnect` | `(init_name, targ_name)` | 断开特定连接 |

**使用规则**:
- 若未调用任何 connect 方法，`_finalize()` 自动调用 `connect_all()`
- `connect_all()` 后可用 `disconnect()` 移除不需要的连接
- `connect()` 的 `targ_names` 是列表: `connect("cpu", ["mem0", "mem1"])`

### 3.11 导出

| 方法 | 签名 | 返回 | 说明 | 详细文档 |
|------|------|------|------|---------|
| `set_export` | `(fmt, simulator, name, ...)` | None | 设置主导出 | [export.md](export.md) |
| `add_export` | `(fmt, simulator, name, ...)` | None | 添加额外导出 | [export.md](export.md) |
| `get_export_command` | `(pdd_path, output_dir)` | str | 获取 CLI 命令 | [export.md](export.md) |

### 3.12 构建输出

| 方法 | 签名 | 说明 |
|------|------|------|
| `write_pdd` | `(path: str)` | 写入 PDD XML 文件 |

**`write_pdd()` 内部流程**:
1. 调用 `_finalize()`:
   - 为所有 Initiator 生成默认 Flow (覆盖所有连接目标的地址范围)
   - 为所有 Target 确保默认 Flow 存在
   - 若无 connectivity，自动 `connect_all()`
   - 调用 `Architecture.auto_derive()` 生成拓扑
2. 调用 `PddWriter(self).write(path)` 生成 XML

### 3.13 Architecture 访问

```python
noc.architecture  # → Architecture 对象
```

通过 `noc.architecture` 可访问底层拓扑控制 API。详见 [architecture.md](architecture.md)。

## 4. 完整使用示例

### 4.1 最小配置

```python
from flexnoc_dsl import NocProject, AXI

noc = NocProject("simple_noc")
axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64))
clk = noc.add_clock("clk", freq="500MHz")
noc.add_initiator("cpu", protocol=axi, clock=clk)
noc.add_target("mem", protocol=axi, clock=clk, base=0x0, size="1G")
noc.connect_all()
noc.set_export("Verilog")
noc.write_pdd("simple.pdd")
```

### 4.2 完整配置

```python
from flexnoc_dsl import (
    NocProject, AXI, APB, AHB,
    PowerDomain, Voltage
)

noc = NocProject("complex_noc")

# 协议
axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64, id=4))
apb = noc.add_protocol("APB_p", APB(addr=32, data=32))
ahb = noc.add_protocol("AHB_p", AHB(addr=32, data=32))

# 电源
pd = noc.add_power_domain("MAIN_dom", kind="ALWAYS_ON")
vdd = noc.add_voltage("VDD", value="0.81")

# 时钟
clk = noc.add_clock("clk", freq="1GHz", voltage_ref="VDD",
                     power_ref="MAIN_dom")

# QoS
noc.set_urgency_levels(4)
noc.set_arbiter_mode("ROUND_ROBIN")
noc.set_use_error_codes(True)

# 标志
noc.add_mode_flag("secure_mode", port="i_secure", active_value=1)
noc.add_user_flag("0_debug")
noc.add_user_flag("1_privileged")

# Initiators
cpu = noc.add_initiator("cpu", protocol=axi, clock=clk,
                        use_press=True, power_domain="MAIN_dom")

# Targets
mem = noc.add_target("mem", protocol=axi, clock=clk,
                     base=0x0, size="256M",
                     seq_id_allocation="ROUND_ROBIN")
io = noc.add_target("io", protocol=apb, clock=clk,
                    base=0x10000000, size="64K")

# 连接
noc.connect_all()

# 导出
noc.set_export("Verilog", simulator="VCS")
noc.add_export("Verilog", simulator="ModelSim",
               name="exports.synth", synthesis_tool="DC",
               files="SingleFile")

noc.write_pdd("complex.pdd")
```

## 5. 内部状态

| 属性 | 类型 | 说明 |
|------|------|------|
| `_protocols` | dict[str, Protocol] | 已注册协议 |
| `_clocks` | list[ClockDomain] | 时钟域 |
| `_initiators` | list[Initiator] | 发起端 |
| `_targets` | list[Target] | 目标端 |
| `_observers` | list[Observer] | 观察者 |
| `_mode_flags` | list[ModeFlag] | 模式标志 |
| `_user_flags` | list[UserFlag] | 用户标志 |
| `_power_domains` | list[PowerDomain] | 电源域 |
| `_voltages` | list[Voltage] | 电压对象 |
| `_user_ports` | list[Port] | 用户端口 |
| `_connectivity` | dict | 连接映射 (init_name, targ_name) → bool |
| `_urgency_levels` | int | 紧急度级别数 |
| `_use_error_codes` | bool | 是否启用错误码 |
| `_arbiter_mode` | str | 仲裁模式 |
| `_export` | dict | 主导出配置 |
| `_exports` | list[dict] | 所有导出配置 |
| `_noc_registers` | dict | NOC 寄存器配置 |
| `_architecture` | Architecture | 架构层对象 |

## 6. _finalize() 行为

`_finalize()` 在 `write_pdd()` 时自动调用：

1. **Initiator Flow 计算**: 扫描所有连接的 Target，计算总地址范围，生成默认 Flow（含正确掩码）
2. **Target Flow 确认**: 确保每个 Target 有默认 Flow
3. **缺省连接**: 若 `_connectivity` 为空，自动 `connect_all()`
4. **架构自动推导**: `Architecture.auto_derive()` 根据时钟域和 socket 列表生成 DTP switch + link 拓扑

**注意**: `_finalize()` 是幂等的，可多次调用。但每次 `write_pdd()` 都会调用一次。
