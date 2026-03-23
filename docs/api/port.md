# Port / ModeFlag / UserFlag / Observer API

> 模块: `flexnoc_dsl.port`
> 职责: 定义端口、模式标志、用户标志和错误观察器

---

## 1. Port — 端口

### 1.1 Port dataclass

```python
@dataclass
class Port:
    name: str              # 端口名
    port_type: str         # "Clock", "ResetN", "TestMode", "Mode", "User"
    clock_ref: str = ""    # 时钟引用 ("None" = 异步)
    width: int = 1         # 位宽
    direction: str = ""    # "Input" / "Output" (仅 User 类型)
    default_val: int|None = None  # 仿真默认值
```

### 1.2 端口类型

| port_type | 说明 | 创建方式 | 自动生成 |
|-----------|------|---------|---------|
| `Clock` | 时钟输入 | `add_clock()` | ✅ 自动 |
| `ResetN` | 低有效复位 | `add_clock()` | ✅ 自动 |
| `TestMode` | 测试模式 | `add_clock()` | ✅ 自动 (多时钟域共享) |
| `Mode` | Remap 模式输入 | `add_mode_flag()` | ✅ 自动 |
| `User` | 用户自定义 I/O | `add_user_port()` | ❌ 手动 |

### 1.3 创建用户端口: `noc.add_user_port()`

```python
port = noc.add_user_port(name, direction, width, clock, default)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `name` | str | *必填* | 合法标识符 | port name | 端口名 |
| `direction` | str | `"Input"` | `"Input"`, `"Output"` | type/direction | 方向 |
| `width` | int | 1 | 1–1024 | type/width | 位宽 |
| `clock` | ClockDomain | None | 已创建 ClockDomain 或 None | type/clock | 时钟域。None → clock="None" (异步) |
| `default` | int | None | ≥ 0 | simulationModel/defaultVal | 仿真默认值。None → 不输出 |

**返回**: `Port` 对象

**PDD 输出**:
```xml
<object kind="port" name="irq_out">
  <properties>
    <entry key="type" value="User">
      <entry key="clock" value="None"/>
      <entry key="direction" value="Output"/>
      <entry key="width" value="1"/>
    </entry>
  </properties>
</object>
```

带仿真默认值:
```xml
<entry key="type" value="User">
  <entry key="clock" value="(specification:clk_dom/Cm/Clk)"/>
  <entry key="direction" value="Input"/>
  <entry key="simulationModel" value="CONSTANT">
    <entry key="defaultVal" value="0"/>
  </entry>
  <entry key="width" value="4"/>
</entry>
```

### 1.4 自动生成的端口

`press` 端口在任意 Initiator 设置 `use_press=True` 时自动生成:
- 类型: `User`, 方向: `Input`
- 宽度: `nUrgencyLevel` (默认 2)
- 仿真默认值: 0 (`simulationModel=CONSTANT, defaultVal=0`)

---

## 2. ModeFlag — 模式标志

用于地址 remap: 一个物理端口驱动一个逻辑标志，mapping 根据标志值选择不同地址。

### 2.1 创建: `noc.add_mode_flag()`

```python
mf = noc.add_mode_flag(name, port, active_value)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `name` | str | *必填* | 合法标识符 | modeFlag name | 逻辑标志名 |
| `port` | str | `name.lower()` | 合法标识符 | port(Mode) name | 驱动端口名 |
| `active_value` | int | 1 | 0, 1 | modePortValues 值 | 激活值 |

**返回**: `ModeFlag` 对象

### 2.2 PDD 生成

每个 ModeFlag 生成:
1. `<object kind="modeFlag">` — 含 `modePortValues`
2. `<object kind="port">` (type=Mode) — 如果同名端口不存在

```xml
<object kind="modeFlag" name="boot_mode">
  <properties>
    <entry key="modePortValues">
      <entry key="(specification:boot_sel)" value="1"/>
    </entry>
  </properties>
</object>
```

### 2.3 使用示例

```python
boot = noc.add_mode_flag("boot_mode", port="boot_sel", active_value=1)

# 在 mapping 中引用
flow.add_mapping("rom",  base=0x0, size="64K",  mode={boot: True})   # boot 时访问 ROM
flow.add_mapping("dram", base=0x0, size="256M", mode={boot: False})  # 正常时访问 DRAM
```

---

## 3. UserFlag — 用户标志

用于 AXI 信号分组映射，常见用途: secure/privileged/debug 信号。

### 3.1 创建: `noc.add_user_flag()`

```python
uf = noc.add_user_flag(name)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `name` | str | *必填* | 约定格式: `"N_label"` | userFlag name | 标志名 |

**命名约定**: `"0_debug"`, `"1_privileged"`, `"2_secureN"`, `"3_dataN"` — 数字前缀+下划线+标签名。

**返回**: `UserFlag` 对象

### 3.2 PDD 生成

```xml
<object disabled="0" kind="userFlag" name="0_debug">
  <properties/>
</object>
```

### 3.3 与 userMapping 的配合

UserFlag 定义后，需在 Initiator 和 Target 的 `user_mapping` 中引用:

**Initiator — driving (驱动)**:
```python
init.user_mapping = {
    "userFlags": {
        "0_debug": "CONST_0",       # 常量 0 驱动
        "1_privileged": "CONST_0",
        "2_secureN": "CONST_0",
    }
}
```

PDD 输出:
```xml
<entry key="userMapping">
  <entry key="driving">
    <entry key="userFlags">
      <entry key="(specification:0_debug)" value="CONST_0"/>
      ...
    </entry>
  </entry>
</entry>
```

**Target — receiving (接收)**:
```python
targ.user_mapping = {
    "ARCache": {"2_secureN": 0, "1_privileged": 1, "0_debug": 2},
    "AWCache": {"2_secureN": 0, "1_privileged": 1, "0_debug": 2},
    "Prot": {"0_debug": 0, "1_privileged": 1, "2_secureN": 2},
}
```

PDD 输出:
```xml
<entry key="userMapping">
  <entry key="ARCache">
    <entry key="userFlags">
      <entry key="(specification:2_secureN)" value="#0"/>
      <entry key="(specification:1_privileged)" value="#1"/>
      ...
    </entry>
  </entry>
</entry>
```

**约束**: 当项目有 UserFlag 时，AXI target 的 userMapping 使用 userFlag 模式（而非默认 CONST_0 specials）。

---

## 4. Observer — 错误观察器

### 4.1 创建: `noc.add_observer()`

```python
obs = noc.add_observer(name, clock)
```

| 参数 | 类型 | 默认值 | 取值范围 | 说明 |
|------|------|--------|---------|------|
| `name` | str | *必填* | 合法标识符 | observer 名 |
| `clock` | ClockDomain | None | 已创建 ClockDomain | 时钟域 |

**返回**: `Observer` 对象

### 4.2 Observer dataclass

```python
@dataclass
class Observer:
    name: str
    clock: ClockDomain = None
    clock_ref: str = ""
    watched_targets: list = []      # 监视的 target 名列表
    interrupt_port: str = ""        # 中断输出端口名
    debug_output: str = "None"      # 调试输出模式
    error_loggers: dict = {}        # 错误日志器配置
```

### 4.3 配置 Observer

`add_observer()` 返回对象后，通过属性设置完整配置:

```python
obs = noc.add_observer("obs_0", clock=clk)
obs.watched_targets = ["targ_0", "targ_1"]
obs.interrupt_port = "irq_out"
```

### 4.4 PDD 生成

Observer 影响 3 个层:

| 层 | 生成物 |
|----|--------|
| specification | `<object kind="observer">` (clock, debugOutput, errorLoggers) |
| architecture | `obsSwitch` + `observationRoute` (自动派生) |
| structure | shadow (含 tacticalPorts → interrupt 端口映射) |

```xml
<object kind="observer" name="obs_0">
  <properties>
    <entry key="clock" value="(specification:clk_domain/Cm/Clk)"/>
    <entry key="debugOutput" value="None"/>
    <entry key="errorLoggers">
      <entry key="0" value="#Standard filtering"/>
    </entry>
  </properties>
</object>
```

---

## 5. 冲突与约束

| 场景 | 约束 | 后果 |
|------|------|------|
| ModeFlag port 与 User port 同名 | ⚠️ 冲突 | 端口会重复定义 |
| UserFlag + specials_mapping | UserFlag 优先 | specials_mapping 被忽略 |
| Observer 无 interrupt_port | ✅ 允许 | structure 中无 tacticalPorts |
| 多 Observer 共用 clock | ✅ 允许 | 各自独立的 obsSwitch |
