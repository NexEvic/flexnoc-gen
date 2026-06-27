# noc2pdd — FlexNoC Python DSL 文档

> 版本: 2.0 | 目标 FlexNoC: 5.3.0 | Python 3.8+

## 项目简介

noc2pdd 是一个 Python DSL，用于以编程方式生成 FlexNoC PDD (Project Design Description) 文件。
用户只需描述 NoC 的 specification 层（协议、时钟、socket、连接），DSL 自动派生 architecture 和 structure 层，
最终由 FlexNoC 工具导出 Verilog RTL。

## 快速开始

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

**验证**: 上述代码 → 458 行 PDD → FlexNoC 导出 31,813 行 Verilog RTL ✅

## 安装

```bash
cd ~/flexnoc-work/noc2pdd
# 无需 pip install，直接 import
# 如果 FlexNoC bashrc 被 source 过，需先清理：
unset PYTHONHOME && unset PYTHONPATH
```

## 设计哲学

| 原则 | 说明 |
|------|------|
| **Specification-only** | 用户只描述"做什么"（socket、协议、连接） |
| **Architecture 自动派生** | crossbar 拓扑全部自动计算 |
| **Structure 自动派生** | FlexNoC 通过 `-d False` 自动填充 |
| **手动覆盖** | 需要自定义拓扑时，通过 `noc.architecture` 接口手动控制 |

## 文档索引

### API 参考

| 文档 | 内容 | 核心类/函数 |
|------|------|-----------|
| [protocol.md](api/protocol.md) | 协议定义 | `AXI()`, `APB()`, `OCP()`, `AHB()`, `AXI_Lite()`, `ACE_Lite()` |
| [clock.md](api/clock.md) | 时钟域、频率解析、多时钟 CDC | `ClockDomain`, `add_clock()` |
| [socket.md](api/socket.md) | Initiator/Target/Flow/Mapping、地址交织 | `add_initiator()`, `add_target()`, `add_interleaved_targets()` |
| [port.md](api/port.md) | 端口、ModeFlag、UserFlag、Observer | `add_user_port()`, `add_mode_flag()`, `add_user_flag()`, `add_observer()` |
| [power.md](api/power.md) | 电源域、电压域、活动区域 | `add_power_domain()`, `add_voltage()` |
| [architecture.md](api/architecture.md) | 自动/手动拓扑、Pipeline、仲裁策略 | `Architecture`, `DtpSwitch`, `DtpLink` |
| [export.md](api/export.md) | 导出选项、多导出、customerCells | `set_export()`, `add_export()` |
| [project.md](api/project.md) | NocProject 顶层 API 汇总 | `NocProject`, `write_pdd()`, `connect_all()` |

### 指南

| 文档 | 内容 |
|------|------|
| [docker-e2e.md](guides/docker-e2e.md) | Docker E2E 验证完整流程 |
| [feature-compatibility.md](guides/feature-compatibility.md) | Feature 冲突矩阵与约束 |

### 案例库

| 文档 | 内容 |
|------|------|
| [cases/index.md](cases/index.md) | FlexNoC/PDD 已知失败案例与 debug 入口 |

### 其他

| 文档 | 内容 |
|------|------|
| [feature_checklist.md](feature_checklist.md) | Feature 实现进度跟踪 |

## PDD 三层结构

```
PDD File
├── protocol (disabled="0")        ← 协议定义
├── specification (disabled="0")   ← 用户配置层（socket/port/clock/power）
├── switchBasedArchitecture (disabled="1")  ← 拓扑层（自动/手动派生）
├── switchBasedStructure (disabled="1")     ← 物理映射层（FlexNoC 自动填充）
├── folder: exports                ← 导出文件夹
└── exportOption                   ← 导出配置
```

- `disabled="0"`: 已配置，FlexNoC 读取
- `disabled="1"`: 由 FlexNoC `-d False` 自动填充

## 导入方式

```python
# 基础导入（覆盖 90% 场景）
from flexnoc_dsl import NocProject, AXI, APB, OCP

# 完整导入
from flexnoc_dsl import (
    NocProject, AXI, APB, OCP, AHB, AXI_Lite, ACE_Lite, Protocol,
    ClockDomain, Initiator, Target, Flow, Mapping,
    compute_interleave_mask, create_interleaved_mappings,
    Port, ModeFlag, Observer, UserFlag, PowerDomain, Voltage,
    Architecture, DtpSwitch, DtpLink, SrvSwitch, ObsSwitch, Route,
)
```
