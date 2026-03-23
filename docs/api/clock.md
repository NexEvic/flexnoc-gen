# Clock API

> 模块: `flexnoc_dsl.clock`
> 职责: 定义时钟域、频率、相关端口、电压和电源引用

---

## 1. 概述

每个 NoC 设计至少需要一个时钟域。时钟域定义了频率、时钟端口、复位端口和测试模式端口。
多时钟域设计时，DSL 自动生成 CDC FIFO (dtpLink) 进行跨时钟域数据传输。

**工作流**:
```python
clk = noc.add_clock("clk_domain", freq="500MHz", port="clk", reset="rst_n")
# → 在 PDD 中生成 clockRegime + clockManager + clock + port(Clock) + port(ResetN) + port(TestMode)
```

## 2. ClockDomain dataclass

```python
@dataclass
class ClockDomain:
    name: str               # 时钟域名 (= clockRegime 名)
    frequency: float        # 频率 (Hz)
    port_name: str          # Clock 端口名
    reset_name: str         # ResetN 端口名
    test_mode: str = "Tm"   # TestMode 端口名
    manager_name: str = "Cm"  # ClockManager 名
    clock_name: str = "Clk"   # Clock 对象名
    clock_type: str = "Root"  # "Root" 或 "Gated"
    voltage_ref: str = ""     # 电压域引用名
    comment: str = ""         # 注释
    power_ref: str = ""       # 电源域/活动区域引用
```

**引用路径属性**:

| 属性 | 格式 | 用途 |
|------|------|------|
| `clock_ref` | `(specification:name/Cm/Clk)` | specification 层内引用 |
| `arch_clock_ref` | `(switchBasedArchitecture:name/Cm/Clk)` | architecture 层内引用 |

## 3. 创建时钟域: `noc.add_clock()`

```python
clk = noc.add_clock(name, freq, port, reset, test_mode, clock_type,
                    voltage_ref, comment, power_ref)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `name` | str | *必填* | 合法标识符 | clockRegime name | 时钟域名，全项目唯一 |
| `freq` | str/int/float | `"500MHz"` | 正数，支持后缀 | `frequency` | 频率 |
| `port` | str | `"clk"` | 合法标识符 | port(Clock) name | 时钟输入端口名 |
| `reset` | str | `"rst_n"` | 合法标识符 | port(ResetN) name | 复位端口名（低有效） |
| `test_mode` | str | `"Tm"` | 合法标识符 | port(TestMode) name | 测试模式端口名 |
| `clock_type` | str | `"Root"` | `"Root"`, `"Gated"` | clock/type | 时钟类型 |
| `voltage_ref` | str | `""` | 已注册的 Voltage 名 | clockRegime/voltage | 电压域引用 |
| `comment` | str | `""` | 任意字符串 | clockRegime/comment | 设计者注释 |
| `power_ref` | str | `""` | 电源域路径 | clockManager/domainLvl/power | 电源域引用 |

**返回**: `ClockDomain` 对象

## 4. 频率解析

`freq` 参数支持多种格式：

| 输入 | 解析结果 (Hz) |
|------|-------------|
| `"500MHz"` | 500,000,000.0 |
| `"1GHz"` | 1,000,000,000.0 |
| `"100KHz"` | 100,000.0 |
| `"50Hz"` | 50.0 |
| `"266e6"` | 266,000,000.0 |
| `266000000` | 266,000,000.0 |
| `500_000_000.0` | 500,000,000.0 |

后缀不区分大小写（`mhz` = `MHz` = `MHZ`）。

## 5. PDD 生成效果

每个 ClockDomain 自动生成以下 PDD 对象（在 specification 层内）:

```xml
<!-- 1. clockRegime 对象 -->
<object kind="clockRegime" name="clk_domain">
  <properties>
    <entry key="comment" value="#注释"/>          <!-- 仅 comment 非空时 -->
    <entry key="frequency" value="500000000.0"/>
    <entry key="voltage" value="(specification:VDD)"/>  <!-- 仅 voltage_ref 非空时 -->
    <!-- 2. clockManager 子对象 -->
    <object kind="clockManager" name="Cm">
      <properties>
        <entry key="domainLvl">
          <entry key="power" value="(specification:NoC_dom)"/>  <!-- 仅 power_ref 非空时 -->
        </entry>
        <entry key="internalLvl">
          <entry key="mainSignals">
            <entry key="resetN" value="(specification:rst_n)"/>
            <entry key="rootClock" value="(specification:clk)"/>
            <entry key="testMode" value="(specification:Tm)"/>
          </entry>
        </entry>
      </properties>
      <!-- 3. clock 子对象 -->
      <object kind="clock" name="Clk">
        <properties>
          <entry key="type" value="Root"/>
        </properties>
      </object>
    </object>
  </properties>
</object>

<!-- 4-6. 自动生成的端口 -->
<object kind="port" name="clk">...</object>       <!-- Clock -->
<object kind="port" name="rst_n">...</object>      <!-- ResetN -->
<object kind="port" name="Tm">...</object>         <!-- TestMode（共享） -->
```

## 6. 时钟类型

| 类型 | PDD value | 说明 |
|------|-----------|------|
| `"Root"` | `Root` | 根时钟，直接由外部时钟源驱动 |
| `"Gated"` | `Gated` | 门控时钟，可被 clockGating 控制 |

## 7. 多时钟域 (CDC)

当不同 socket 使用不同时钟域时，auto_derive 自动生成 CDC FIFO：

```python
clk_a = noc.add_clock("domain_a", "500MHz", port="clk_a", reset="rst_a_n")
clk_b = noc.add_clock("domain_b", "200MHz", port="clk_b", reset="rst_b_n")

noc.add_initiator("init_0", protocol=axi, clock=clk_a)
noc.add_target("targ_0", protocol=axi, clock=clk_b)
# → 自动生成:
#   domain_a: dtpSwitch000 (rsp) + dtpSwitch001 (req)
#   domain_b: dtpSwitch002 (rsp) + dtpSwitch003 (req)
#   跨域: fifo_req_000 (domain_a→b) + fifo_rsp_000 (domain_b→a)
```

**CDC FIFO 默认参数**:
- `buffering = "FIFO"`
- `n_byte = 32`
- `n_packet = 4`

**端口共享**: 多个时钟域共享同一个 TestMode 端口 (`Tm`)，DSL 自动去重。

## 8. voltage_ref 依赖

当设置 `voltage_ref` 时，必须先通过 `noc.add_voltage()` 注册对应的电压对象：

```python
v = noc.add_voltage("VDD", value="0.81")
clk = noc.add_clock("clk_dom", freq="500MHz", voltage_ref="VDD")
# → clockRegime 中生成 <entry key="voltage" value="(specification:VDD)"/>
```

**约束**: `voltage_ref` 的值必须是已注册的 Voltage 对象名，否则生成的 PDD 引用无效。

## 9. power_ref 依赖

当设置 `power_ref` 时，必须先通过 `noc.add_power_domain()` 注册对应的电源域：

```python
pd = noc.add_power_domain("NoC_dom", kind="ALWAYS_ON")
clk = noc.add_clock("clk_dom", freq="500MHz", power_ref="NoC_dom")
# → clockManager/domainLvl 中生成 <entry key="power" value="(specification:NoC_dom)"/>
```

**支持路径格式**: `"NoC_dom"` 或 `"NoC_dom/NoC_zone"`（电源域/活动区域）

**⚠️ 关键约束**: 当项目中存在 **任何** PowerDomain 对象时，clockManager 的 `power_ref` **必须**设置，
否则 FlexNoC 导出时报错 `"Missing parameter setting for domainLvl..power"`。

## 10. 冲突与约束

| 场景 | 约束 | 后果 |
|------|------|------|
| 有 PowerDomain 但 power_ref 为空 | ❌ 必须设置 | FlexNoC 报错 |
| voltage_ref 引用不存在的 Voltage | ⚠️ 无效引用 | FlexNoC 可能报错 |
| 多时钟域 + 相同 port 名 | ✅ 允许 | 自动去重，共用一个端口 |
| 多时钟域 + 不同 test_mode 名 | ✅ 允许 | 各自生成独立 TestMode 端口 |
| clock_type="Gated" + 无 clockGating | ✅ 允许 | 时钟默认不门控 |
