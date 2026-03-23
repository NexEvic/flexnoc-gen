# Feature 兼容性与约束矩阵

> 记录所有 feature 之间的冲突、依赖和互斥关系

---

## 1. 协议兼容性矩阵

### 1.1 协议与 Socket 参数兼容性

| 参数 | AXI | APB | OCP_Lite | AHB | AXI_Lite | ACE_Lite |
|------|-----|-----|----------|-----|----------|----------|
| `pending_trans` | 1-256 | 1-256 | 1-256 | **仅 1** | 1-256 | 1-256 |
| `pending_ids` | 0-256 | 0-256 | 0-256 | 0-256 | 0-256 | 0-256 |
| `use_press` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `use_soft_lock` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `clock_gating` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `seq_id_allocation` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `conversion` | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `specials_mapping` | ✅ Target | ❌ | ❌ | ❌ | ❌ | ❌ |

### 1.2 AHB 特殊约束

| 约束 | 说明 |
|------|------|
| `pending_trans` | 最大值为 1 (AHB 不支持乱序) |
| PDD 协议类型 | 生成 `AHB` (非 `AXI`) |
| userMapping | 自动添加 `HProt`, `XorHProt_6` |
| `enRead`/`enWrite`/`useFixed` | 不输出 (AHB 不支持) |
| 与 AXI 混合 | 自动添加 `nReassemblyBuffer=2` |

### 1.3 混合协议规则

当 NoC 中同时存在不同协议类型时:

| 场景 | 自动行为 |
|------|---------|
| AXI + APB | 自动添加 `nReassemblyBuffer=2` 到 AXI initiator shadow |
| AXI + AHB | 同上 |
| AXI + OCP | 同上 |
| 纯 AXI | 不添加 nReassemblyBuffer |
| 纯 APB | 不添加 nReassemblyBuffer |

**检测逻辑** (`_needs_reassembly`): 检查所有 initiator/target 的协议类型，若存在多种类型则返回 True。

## 2. 电源系统依赖

### 2.1 PowerDomain → ClockDomain

| 条件 | 要求 |
|------|------|
| 存在任何 PowerDomain | ClockDomain 必须设置 `power_ref` 指向一个 PowerDomain |
| 存在 PowerDomain | PDD 自动生成 `clockManager` 节点 |

### 2.2 Voltage → ClockDomain

| 条件 | 要求 |
|------|------|
| 存在 Voltage | ClockDomain 可选设置 `voltage_ref` |
| `voltage_ref` 设置 | clock regime 中添加电压引用 |

### 2.3 PowerDomain 类型约束

| 类型 | 约束 | 说明 |
|------|------|------|
| `ALWAYS_ON` | 无特殊约束 | 安全默认值 |
| `SUPPLY` | 需要 powerController 配置 | FlexNoC 要求 |
| `SWITCHABLE` | 需要关联控制信号 | 复杂配置 |

### 2.4 IP PowerDomain

当 socket 设置 `power_domain` 时:
- 在 spec socket 条目中添加 `<entry key="IPpowerDomain" value="DOMAIN_NAME"/>`
- domain 名必须与已注册的 PowerDomain 匹配

## 3. usePress 依赖链

当任何 Initiator 设置 `use_press=True`:

| 组件 | 自动行为 |
|------|---------|
| spec_ports | 自动添加 Press 端口 (User/Input, width=nUrgencyLevel) |
| arch_shadow | 添加 `usePress=True` |
| struct_shadow | 添加 tacticalPorts/main/Press 映射 |
| urgency_levels | 决定 press 端口位宽 |

**约束**: `urgency_levels` 需在 `write_pdd()` 之前设置好。

## 4. userMapping 与 UserFlag 依赖

### 4.1 AXI userMapping (Target 侧)

当 Target 有 UserFlag 时，每个 UserFlag 生成:
- `awuser[N]`: Write address channel mapping
- `aruser[N]`: Read address channel mapping
- `wuser[N]`: Write data channel mapping

其中 N = UserFlag 名中的数字 (如 `0_debug` → N=0)

### 4.2 AHB userMapping (Target 侧)

AHB Target 固定生成:
- `HProt`: HProtocol 映射
- `XorHProt_6`: HProt bit 6 XOR 映射

### 4.3 specials_mapping (Target 侧)

仅 AXI Target 支持:
```python
specials_mapping={
    "awcache[0]": "Bufferable",
    "awcache[1]": "Modifiable",
}
```

## 5. Architecture 约束

### 5.1 auto_derive 规则

| 条件 | 拓扑 |
|------|------|
| 单时钟域 | 1 个 DtpSwitch + N 个 DtpLink |
| 多时钟域 | 每个时钟域 1 个 DtpSwitch + Srv/Obs Switch |
| 有 Observer | 自动添加 ObsSwitch |
| 有 noc_registers | 自动添加 SrvSwitch |

### 5.2 arbitration 全局设置

`arbiter_mode` 影响所有 DtpSwitch 的仲裁策略:
- 在 arch globals 中设置 `defaultArbiterMode`
- 所有 switch 继承此设置

## 6. Export 约束

### 6.1 多 Export 冲突

| 场景 | 结果 |
|------|------|
| 多个同名 export | PDD 中出现重复节点 ⚠️ |
| 无 export | 可生成 PDD 但无法通过 FlexNoC CLI 导出 |

### 6.2 customerCells

- 路径在 PDD 中前缀 `#`
- 实际路径必须在 Docker 容器内可见
- 常用挂载路径: `/work/cells/`

## 7. 地址空间约束

| 约束 | 说明 |
|------|------|
| Target 地址不可重叠 (非交织) | 地址空间冲突导致 FlexNoC 错误 |
| 交织 Target 共享地址空间 | 通过条带化分配 |
| 最小条带大小 | 4K (推荐) |
| 总交织大小 | 必须是 stripe_size × num_targets 的倍数 |

## 8. 完整约束速查表

| Feature | 前置依赖 | 冲突项 | 作用范围 |
|---------|---------|--------|---------|
| `use_press` | - | - | Initiator |
| `conversion` | AXI/AHB/AXI_Lite 协议 | APB/OCP | Initiator/Target |
| `specials_mapping` | AXI 协议 | APB/OCP/AHB | Target only |
| `power_domain` (socket) | PowerDomain 已注册 | - | Initiator/Target |
| `power_ref` (clock) | PowerDomain 已注册 | - | ClockDomain |
| `voltage_ref` (clock) | Voltage 已注册 | - | ClockDomain |
| `seq_id_allocation` | - | - | Target |
| AHB 协议 | - | pending_trans>1 | 全局 |
| 多种协议混合 | - | - | 自动 nReassemblyBuffer |
| `clock_type="Gated"` | Root 时钟存在 | 多 Root ⚠️ | ClockDomain |
| `arbiter_mode` | - | - | 全局 |
| `useErrorCodes` | - | - | 全局 |
