# Power & Voltage API

> 模块: `flexnoc_dsl.port` (PowerDomain, Voltage dataclass)
> 职责: 定义电源域、电压域、活动区域

---

## 1. 概述

FlexNoC 支持电源域管理，允许 NoC 的不同部分在不同电源域中运行。
电源域由 PowerDomain 对象定义，电压由 Voltage 对象定义，两者在 specification 层内生成。

**依赖关系**:
```
Voltage ← clockRegime (voltage_ref)
PowerDomain ← clockManager (power_ref)
PowerDomain ← socket (power_domain → IPpowerDomain)
ActivityZone ← PowerDomain 的子对象
```

## 2. PowerDomain — 电源域

### 2.1 创建: `noc.add_power_domain()`

```python
pd = noc.add_power_domain(name, kind, comment, activity_zones)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `name` | str | *必填* | 合法标识符 | power object name | 电源域名 |
| `kind` | str | `"ALWAYS_ON"` | `"ALWAYS_ON"`, `"SUPPLY"`, `"SWITCHABLE"` | domainLvl/kind | 域类型 |
| `comment` | str | `""` | 任意字符串 | domainLvl/comment | 注释 |
| `activity_zones` | list | `[]` | 字符串列表 | 子 activityZone 对象 | 活动区域名列表 |

**返回**: `PowerDomain` 对象

### 2.2 电源域类型

| kind | 说明 | 需要 interfaceLvl | 额外配置 |
|------|------|-----------------|---------|
| `ALWAYS_ON` | 常开域，永不关断 | ❌ 不需要 | 无 |
| `SUPPLY` | 可切换电源供应域 | ✅ 需要 | 需要 powerController 配置 |
| `SWITCHABLE` | 可切换域 | ✅ 需要 | 需要 powerController 配置 |

**约束**:
- ⚠️ `SUPPLY` 和 `SWITCHABLE` 会自动生成 `interfaceLvl/powerController=None`，但完整 powerController 配置在当前 DSL 中未实现
- ✅ `ALWAYS_ON` 可直接使用，最简单且安全

### 2.3 Activity Zone

ActivityZone 是 PowerDomain 的子对象，用于更细粒度的电源控制:

```python
pd = noc.add_power_domain("NoC_dom", kind="ALWAYS_ON",
                          activity_zones=["NoC_zone"])
# → 在 NoC_dom 下生成 <object kind="activityZone" name="NoC_zone">
```

**power_ref 引用格式**: `"NoC_dom"` (仅电源域) 或 `"NoC_dom/NoC_zone"` (电源域/活动区域)

### 2.4 PDD 生成

```xml
<!-- ALWAYS_ON 域 -->
<object kind="power" name="INTERCO_dom">
  <properties>
    <entry key="domainLvl">
      <entry key="comment" value="#kind TBD"/>
      <entry key="kind" value="ALWAYS_ON"/>
    </entry>
  </properties>
</object>

<!-- SUPPLY 域 (含 interfaceLvl) -->
<object kind="power" name="ext_dom">
  <properties>
    <entry key="domainLvl">
      <entry key="kind" value="SUPPLY"/>
    </entry>
    <entry key="interfaceLvl">
      <entry key="powerController" value="None"/>
    </entry>
  </properties>
</object>

<!-- 含 ActivityZone -->
<object kind="power" name="NoC_dom">
  <properties>
    <entry key="domainLvl">
      <entry key="kind" value="ALWAYS_ON"/>
    </entry>
  </properties>
  <object kind="activityZone" name="NoC_zone">
    <properties/>
  </object>
</object>
```

## 3. Voltage — 电压域

### 3.1 创建: `noc.add_voltage()`

```python
v = noc.add_voltage(name, value, comment)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `name` | str | *必填* | 合法标识符 | voltage object name | 电压域名 |
| `value` | str | `"0.81"` | 数字字符串 | properties/value | 电压值 (V) |
| `comment` | str | `""` | 任意字符串 | properties/comment | 注释 |

**返回**: `Voltage` 对象

### 3.2 PDD 生成

```xml
<object kind="voltage" name="VDD">
  <properties>
    <entry key="comment" value="#TBD by designer"/>
    <entry key="value" value="0.81"/>
  </properties>
</object>
```

## 4. Socket 电源域引用 (IPpowerDomain)

通过 `add_initiator()` 或 `add_target()` 的 `power_domain` 参数引用电源域:

```python
pd = noc.add_power_domain("NoC_dom", kind="ALWAYS_ON")
init = noc.add_initiator("cpu", protocol=axi, clock=clk,
                         power_domain="NoC_dom")
```

**PDD 输出**:
```xml
<object kind="socket" name="cpu">
  <properties>
    ...
    <entry key="power">
      <entry key="IPpowerDomain" value="(specification:NoC_dom)"/>
    </entry>
    ...
  </properties>
</object>
```

## 5. Clock 电源引用 (clockManager power)

通过 `add_clock()` 的 `power_ref` 参数引用:

```python
clk = noc.add_clock("clk_dom", freq="500MHz", power_ref="NoC_dom")
```

**PDD 输出**:
```xml
<object kind="clockManager" name="Cm">
  <properties>
    <entry key="domainLvl">
      <entry key="power" value="(specification:NoC_dom)"/>
    </entry>
    ...
  </properties>
</object>
```

## 6. Clock 电压引用 (clockRegime voltage)

通过 `add_clock()` 的 `voltage_ref` 参数引用:

```python
v = noc.add_voltage("VDD", value="0.81")
clk = noc.add_clock("clk_dom", freq="500MHz", voltage_ref="VDD")
```

**PDD 输出**:
```xml
<object kind="clockRegime" name="clk_dom">
  <properties>
    <entry key="voltage" value="(specification:VDD)"/>
    ...
  </properties>
</object>
```

## 7. 完整示例

```python
noc = NocProject("power_example")
axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64, id=4))

# 电压域
v = noc.add_voltage("VDD_0p81", value="0.81", comment="#Core voltage")

# 电源域 + 活动区域
pd = noc.add_power_domain("NoC_dom", kind="ALWAYS_ON",
                          comment="#NoC power", activity_zones=["NoC_zone"])

# 时钟域引用电压和电源
clk = noc.add_clock("clk_dom", freq="500MHz",
                    voltage_ref="VDD_0p81", power_ref="NoC_dom")

# Socket 引用电源域
noc.add_initiator("cpu", protocol=axi, clock=clk, power_domain="NoC_dom")
noc.add_target("mem", protocol=axi, clock=clk, base=0, size="256M",
               power_domain="NoC_dom")
```

## 8. 冲突与约束

| 场景 | 约束 | 后果 |
|------|------|------|
| 有 PowerDomain 但 clock power_ref 为空 | ❌ 必须设置 | FlexNoC 报错: "Missing parameter setting for domainLvl..power" |
| SUPPLY 域无 powerController 配置 | ⚠️ 限制 | 生成 `powerController=None`，可能需手动编辑 PDD |
| voltage_ref 引用不存在的 Voltage | ⚠️ 无效引用 | FlexNoC 可能报错 |
| power_domain 引用不存在的 PowerDomain | ⚠️ 无效引用 | FlexNoC 可能报错 |
| 无 PowerDomain 但设了 power_ref | ✅ 允许 | 生成引用但可能无效 |
| ActivityZone 无 PowerDomain 父节点 | — | 不会发生（ActivityZone 是 PowerDomain 的子对象） |
