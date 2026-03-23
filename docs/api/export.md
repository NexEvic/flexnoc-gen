# Export API

> 模块: `flexnoc_dsl.project` (NocProject methods)
> 职责: 配置 Verilog/SystemC 导出选项，支持多导出、综合工具、customerCells

---

## 1. 概述

Export 配置定义了 FlexNoC 如何从 PDD 导出 RTL。支持:
- 单个或多个导出选项
- 不同仿真器 (VCS、ModelSim、Xcelium)
- 综合工具支持 (DC、Genus)
- 自定义 cell 替换 (customerCells)
- 文件合并 (SingleFile)

## 2. 基本导出: `noc.set_export()`

```python
noc.set_export(fmt, simulator, name, synthesis_tool, files, customer_cells)
```

| 参数 | 类型 | 默认值 | 取值范围 | PDD key | 说明 |
|------|------|--------|---------|---------|------|
| `fmt` | str | `"Verilog"` | `"Verilog"`, `"SystemC"` | exportOption value | 导出格式 |
| `simulator` | str | `"VCS"` | `"VCS"`, `"ModelSim"`, `"Xcelium"` | simulator | 仿真器 |
| `name` | str | 自动 | 合法标识符 | exportOption name | 导出名 |
| `synthesis_tool` | str | `""` | `""`, `"DC"`, `"Genus"` | synthesisTool | 综合工具 |
| `files` | str | `""` | `""`, `"SingleFile"` | files | 文件合并模式 |
| `customer_cells` | dict | `{}` | `{cell_name: path}` | customerCells | 自定义 cell |

**自动命名**: `name` 为空时自动生成:
- Verilog → `"exports.Vlog"`
- SystemC → `"exports.SystemC"`

**注意**: `set_export()` 同时设置 `_export`（用于导出命令生成）和添加到 `_exports` 列表。

## 3. 多导出: `noc.add_export()`

```python
noc.add_export(fmt, simulator, name, synthesis_tool, files, customer_cells)
```

参数与 `set_export()` 完全相同。用于添加额外的导出配置:

```python
# 仿真导出
noc.set_export("Verilog", simulator="VCS", name="exports.Vlog")

# 综合导出
noc.add_export("Verilog", simulator="ModelSim",
               name="exports.synthesisDC",
               synthesis_tool="DC",
               files="SingleFile",
               customer_cells={
                   "GaterCell": "/path/to/gater.v",
                   "SynchronizerCell": "/path/to/sync.v",
               })
```

## 4. 参数详解

### 4.1 simulator

| 值 | 说明 | 常用场景 |
|----|------|---------|
| `"VCS"` | Synopsys VCS | 仿真 (默认) |
| `"ModelSim"` | Mentor ModelSim | 综合 + 仿真 |
| `"Xcelium"` | Cadence Xcelium | 仿真 |

### 4.2 synthesis_tool

| 值 | 说明 | 效果 |
|----|------|------|
| `""` (空) | 仅仿真 | 不输出 synthesisTool 条目 |
| `"DC"` | Synopsys Design Compiler | 输出 `<entry key="synthesisTool" value="DC"/>` |
| `"Genus"` | Cadence Genus | 输出 `<entry key="synthesisTool" value="Genus"/>` |

### 4.3 files

| 值 | 说明 | 效果 |
|----|------|------|
| `""` (空) | 多文件输出 (默认) | 不输出 files 条目 |
| `"SingleFile"` | 合并为单文件 | 所有 RTL 合并到一个 .v 文件 |

### 4.4 customer_cells

自定义 cell 替换。FlexNoC 默认使用内置的 GaterCell、SynchronizerCell 等。
通过此参数可替换为自定义实现:

```python
customer_cells={
    "GaterCell": "/path/to/my_gater.v",
    "SynchronizerCell": "/path/to/my_sync.v",
}
```

**已知 cell 类型**:
- `GaterCell` — 时钟门控 cell
- `SynchronizerCell` — CDC 同步器 cell
- `ClockManagerCell` — 时钟管理 cell

**PDD 输出**:
```xml
<entry key="customerCells">
  <entry key="GaterCell">
    <entry key="synthesis">
      <entry key="descriptionPath" value="#/path/to/my_gater.v"/>
    </entry>
  </entry>
</entry>
```

注意: 路径前带 `#` 符号。

## 5. 导出命令生成

```python
cmd = noc.get_export_command(pdd_path, output_dir)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pdd_path` | str | *必填* | PDD 文件路径 |
| `output_dir` | str | `"./output"` | 输出目录 |

**返回**: FlexNoC CLI 命令字符串

**示例**:
```python
cmd = noc.get_export_command("my_noc.pdd", "/work/output")
# → "FlexNoC -d False -p my_noc.pdd exportVerilog -s my_noc_struct -c exports.Vlog -o /work/output"
```

**关键参数说明**:
- `-d False`: 让 FlexNoC 自动填充 architecture/structure (disabled 层)
- `-s`: structure 名 (= `{project_name}_struct`)
- `-c`: export option 名
- `-o`: 输出目录

## 6. PDD 结构

导出配置在 PDD 中生成两部分:

```xml
<!-- 1. exports 文件夹 -->
<object kind="folder" name="exports">
  <properties/>
</object>

<!-- 2. exportOption (可多个) -->
<object kind="exportOption" name="exports.Vlog">
  <properties>
    <entry key="exportOption" value="Verilog">
      <entry key="simulator" value="VCS"/>
    </entry>
  </properties>
</object>

<object kind="exportOption" name="exports.synthesisDC">
  <properties>
    <entry key="exportOption" value="Verilog">
      <entry key="customerCells">
        <entry key="GaterCell">
          <entry key="synthesis">
            <entry key="descriptionPath" value="#/path/to/gater.v"/>
          </entry>
        </entry>
      </entry>
      <entry key="files" value="SingleFile"/>
      <entry key="simulator" value="ModelSim"/>
      <entry key="synthesisTool" value="DC"/>
    </entry>
  </properties>
</object>
```

## 7. Docker E2E 导出流程

详见 [docker-e2e.md](../guides/docker-e2e.md)。

简要流程:
```bash
docker run --rm --hostname YunqiLaptop --cap-add NET_ADMIN --entrypoint bash \
  -v ~/flexnoc-work:/work flexnoc:5.3.0-standalone -c '
  ... (license setup) ...
  FlexNoC -d False -p /work/my_noc.pdd exportVerilog \
    -s my_noc_struct -c exports.Vlog -o /work/output
'
```

## 8. 冲突与约束

| 场景 | 约束 | 后果 |
|------|------|------|
| set_export 多次调用 | ⚠️ 累积 | 每次都追加到 _exports 列表 |
| 无 export 配置 | ⚠️ 允许 | PDD 不含 exportOption，无法导出 |
| SystemC 导出 | ⚠️ 未验证 | API 支持但未 E2E 测试 |
| customer_cells 路径不存在 | ⚠️ 运行时错误 | FlexNoC 导出时报错 |
| name 重复 | ⚠️ 可能冲突 | PDD 中多个同名 exportOption |
