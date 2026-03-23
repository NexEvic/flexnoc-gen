# FlexNoC 全特性系统性发现与实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 系统性地发现 FlexNoC 5.3.0 所有可在 PDD 中配置的 feature，逐一逆向工程其 PDD 格式，在 noc2pdd DSL 中实现，并端到端验证。

**Architecture:** 四阶段迭代循环 — (1) 枚举 feature → (2) 逆向 PDD 格式 → (3) 实现+测试+记录经验 → (4) 完整性检查，发现缺失则回到 (1)。每个 feature 独立走完 2→3 小循环后再进入下一个。

**Tech Stack:** Python 3 (DSL), XML (PDD), Docker (FlexNoC 5.3.0-standalone), bash, FlexNoC CLI (`exportVerilog`, `exportAMemoryMap`)

---

## 数据源清单 (已确认可用)

| # | 数据源 | 位置 | 用途 |
|---|--------|------|------|
| D1 | **XHTML 文档 TOC** | Docker: `/opt/flexnoc/5.3.0/share/sw/exported/doc/kbpFN_Arteris/XHTML/toc.htm` | 特性分类与参数名发现 |
| D2 | **sampleproject.pdd** | `~/flexnoc-work/xml-output/sampleproject.pdd` (48KB) | 基础参考 PDD，28 object kinds，~120 unique keys |
| D3 | **PSI_reference_design.pdd** | `~/flexnoc-work/xml-output/PSI_reference_design.pdd` (103KB) | 高级参考 PDD，33 object kinds，~170 unique keys |
| D4 | **FlexVerifier UVM 源码** | Docker: `/opt/flexnoc/5.3.0/share/sw/exported/verif/` | 协议级参数发现 |
| D5 | **FlexNoC CLI** | `FlexNoC -h`, `FlexNoC exportVerilog -h` 等 | 导出选项发现 |
| D6 | **FlexNoC JAR/Python** | Docker: `/opt/flexnoc/5.3.0/TopologyEditor/lib/` | 内部参数名、默认值 |

---

## 已实现 Feature 基线 (30 个)

> 来源: `API_REFERENCE.md` Section 9

AXI/APB/OCP 协议, 单/多时钟域, Gated Clock, Initiator/Target Socket (pending_trans, pending_ids, soft_lock, seq_id_width),
全连接/选择性连接/断开连接, 多 Flow / 多 Mapping, 地址 Remap (ModeFlag), QoS (urgencyLevel),
User Port, Observer (基础), NOC Registers, 自动/手动拓扑, CDC FIFO Link, AXI userMapping,
TestMode 端口, Verilog 导出, 地址交织, 响应交织 (minInterleaveSize)

---

## Phase 1: 全特性枚举 (Feature Enumeration)

### 目标
建立一个 **完整的 feature checklist** (`docs/feature_checklist.md`)，覆盖 FlexNoC 5.3.0 所有可在 PDD 中配置的参数。

### Task 1.1: 从 TOC 提取特性分类树

**Files:**
- Create: `docs/feature_checklist.md`

**Step 1: 用脚本从 TOC 提取主要 feature 类别**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
cat /opt/flexnoc/5.3.0/share/sw/exported/doc/kbpFN_Arteris/XHTML/toc.htm \
  | sed "s/<[^>]*>/\n/g" | grep -v "^$" | grep -v "^[[:space:]]*$" \
  | grep -iE "^(FlexNoC |Addressing|Clocking|Memory Unit|NIU |Generic |Specific |AXI |AHB |APB |OCP |NSP |PIF |Observ|Power |QoS |Resilien|Service|Firewall|Security|Tunnel|VC-Link|FloorPlan|Export)" \
  | head -80
'
```

Expected: 主要功能模块名列表

**Step 2: 创建 feature_checklist.md 初始框架**

基于 TOC 分析结果，按以下分类组织:

```markdown
# FlexNoC Feature Checklist

## 分类说明
- ✅ 已实现并验证
- 🔧 已实现未验证
- ❌ 未实现
- ⬜ 不适用于 PDD DSL (如 GUI-only 功能)

## A. 协议 (Protocol)
- ✅ AXI (V3) — addr/data/id/enRead/enWrite/useFixed
- 🔧 APB — addr/data
- 🔧 OCP — addr/data/id
- ❌ AXI4/AXI5 — wLen, wQos, wRegion 等扩展参数
- ❌ ACE-Lite — useBarrier, withDVMsupport, useEarlyWrRsp
- ❌ AXI-Lite — 轻量版
- ❌ AHB — 独立协议
- ❌ NSP — NoC 间互连协议
- ❌ NSP_BROADCAST — 广播协议
- ❌ PIF — Xtensa 处理器接口
- ⬜ OCP .conf 导入 — 工具特定，非 PDD 生成

## B. 时钟与复位 (Clock & Reset)
...
```

**Step 3: 验证 — 对照 D2/D3 的 object kind 列表，确认无遗漏类别**

Run:
```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
grep -oP "kind=\"[^\"]+\"" /work/PSI_reference_design.pdd | sort -u
' 2>/dev/null
```

Expected: 33 种 object kind，每种必须在 checklist 中有对应条目

---

### Task 1.2: 从参考 PDD 提取参数级 feature

**Step 1: 提取 sampleproject.pdd 中所有 entry key**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
grep -oP "key=\"[^\"]+\"" /work/sampleproject.pdd | sort -u | sed "s/key=\"//;s/\"//"
'
```

Expected: ~120 个 unique key

**Step 2: 提取 PSI_reference_design.pdd 中独有的 entry key (差集)**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
comm -23 \
  <(grep -oP "key=\"[^\"]+\"" /work/PSI_reference_design.pdd | sort -u | sed "s/key=\"//;s/\"//") \
  <(grep -oP "key=\"[^\"]+\"" /work/sampleproject.pdd | sort -u | sed "s/key=\"//;s/\"//")
'
```

Expected: ~50 个额外 key (addressTranslator, ArbiterMode, clockGating, extraPorts, etc.)

**Step 3: 将所有 key 归类到 checklist 对应的 feature 类别中**

对于每个 key，通过在 TOC 中搜索其出现位置来确定所属类别：
```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
grep -i "KEY_NAME" /opt/flexnoc/5.3.0/share/sw/exported/doc/kbpFN_Arteris/XHTML/toc.htm \
  | sed "s/<[^>]*>//g" | head -5
'
```

---

### Task 1.3: 从文档页面发现隐藏参数

有些参数可能不在参考 PDD 中（因为使用默认值），但文档有记录。

**Step 1: 搜索每个 NIU 类型的参数页面**

```bash
# 以 AXI initiator NIU 为例
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
# 找到 AXI initiator NIU 参数相关页面
grep -l "AXI.*initiator.*NIU\|initiator.*AXI.*parameter" \
  /opt/flexnoc/5.3.0/share/sw/exported/doc/kbpFN_Arteris/XHTML/*.htm 2>/dev/null | head -10
'
```

**Step 2: 从参数页面提取参数表**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
# 读取 AXI NIU 参数页面内容，提取 <td> 中的参数名
cat /opt/flexnoc/5.3.0/share/sw/exported/doc/kbpFN_Arteris/XHTML/PAGE_ID.htm \
  | sed "s/<[^>]*>/\n/g" | grep -v "^$" | grep -v "^[[:space:]]*$"
' 
```

**Step 3: 差集比较 — 文档参数 vs PDD 已出现参数**

将文档中发现但参考 PDD 中未出现的参数标记为 "文档记录但无样例" 类别。

---

### Task 1.4: 汇总并生成 Feature Checklist v1

**Files:**
- Modify: `docs/feature_checklist.md`

将 Task 1.1-1.3 的所有发现汇总，生成完整的分类清单。每个条目包含：
- Feature 名称
- 所属类别
- PDD key 名称
- 数据源 (D1-D6 中哪个发现的)
- 当前 DSL 状态 (✅/🔧/❌/⬜)
- 优先级标注 (P0=核心/P1=常用/P2=高级/P3=边缘)

---

## Phase 2: PDD 格式逆向工程方法论 (Per-Feature)

### 目标
对 Phase 1 checklist 中每个 ❌ 状态的 feature，用经过验证的 5 阶段方法逆向出其 PDD XML 格式。

### 通用方法论 (已在 interleave 实现中验证过)

```
┌─────────────────────────────────────────────────────────┐
│  Stage 1: Grep 参考 PDD                                │
│  在 D2/D3 中搜索该 feature 的关键字                      │
│  → 得到: XML 结构片段、object kind、entry key            │
├─────────────────────────────────────────────────────────┤
│  Stage 2: 搜索 FlexNoC 内部                              │
│  在 JAR/Python/FlexVerifier 中搜索 key 名变体            │
│  → 得到: 参数默认值、约束条件、关联参数                    │
├─────────────────────────────────────────────────────────┤
│  Stage 3: 跟踪文档链                                     │
│  从 TOC 找到对应 XHTML 页面，逐页阅读                     │
│  → 得到: 参数含义、取值范围、数学公式、配置规则            │
├─────────────────────────────────────────────────────────┤
│  Stage 4: 实现 DSL                                       │
│  在 flexnoc_dsl 中添加 dataclass + PddWriter 输出        │
│  → 得到: 可生成该 feature 的 PDD XML                     │
├─────────────────────────────────────────────────────────┤
│  Stage 5: 端到端验证                                     │
│  生成 PDD → FlexNoC exportVerilog → 检查输出              │
│  → 得到: ✅ 确认 or 🔴 调试                              │
└─────────────────────────────────────────────────────────┘
```

### Task 2.1: Stage 1 — Grep 参考 PDD (模板)

针对目标 feature `FEATURE_NAME`:

**Step 1: 搜索关键字**

```bash
docker run --rm -v ~/flexnoc-work:/work --entrypoint bash flexnoc:5.3.0-standalone -c '
grep -n -i "KEYWORD" /work/sampleproject.pdd /work/PSI_reference_design.pdd | head -30
'
```

**Step 2: 提取上下文 (找到匹配行号后)**

```bash
docker run --rm -v ~/flexnoc-work:/work --entrypoint bash flexnoc:5.3.0-standalone -c '
sed -n "START_LINE,END_LINEp" /work/PSI_reference_design.pdd
'
```

**Step 3: 记录发现的 XML 结构**

记录到 `docs/pdd_format_notes/FEATURE_NAME.md`:
- Object kind
- Parent-child 层级
- Entry key 名称和值的格式
- 哪个 phase (specification/architecture/structure) 出现

---

### Task 2.2: Stage 2 — 搜索内部实现 (模板)

**Step 1: 在 JAR 文件中搜索参数名**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
find /opt/flexnoc/5.3.0 -name "*.jar" | while read jar; do
  unzip -l "$jar" 2>/dev/null | grep -i "KEYWORD" && echo "  ^ in $jar"
done | head -20
'
```

**Step 2: 在 FlexVerifier 源码中搜索**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
grep -r -l "KEYWORD" /opt/flexnoc/5.3.0/share/sw/exported/verif/ 2>/dev/null | head -10
'
```

**Step 3: 在 Python 脚本中搜索**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
find /opt/flexnoc/5.3.0 -name "*.py" -exec grep -l "KEYWORD" {} \; 2>/dev/null | head -10
'
```

---

### Task 2.3: Stage 3 — 跟踪文档链 (模板)

**Step 1: 在 TOC 中定位**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
grep -i "KEYWORD" /opt/flexnoc/5.3.0/share/sw/exported/doc/kbpFN_Arteris/XHTML/toc.htm \
  | sed "s/<[^>]*>//g" | grep -v "^$" | head -10
'
```

**Step 2: 提取关联的 .htm 页面 ID**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
grep -oP "href=\"[^\"]*KEYWORD[^\"]*\"" \
  /opt/flexnoc/5.3.0/share/sw/exported/doc/kbpFN_Arteris/XHTML/toc.htm \
  | head -5
'
```

**Step 3: 阅读参数页面**

```bash
docker run --rm --entrypoint bash flexnoc:5.3.0-standalone -c '
cat /opt/flexnoc/5.3.0/share/sw/exported/doc/kbpFN_Arteris/XHTML/PAGE_ID.htm \
  | sed "s/<[^>]*>/\n/g" | grep -v "^$" | grep -v "^[[:space:]]*$" | head -100
'
```

**Step 4: 记录参数规格**

在 `docs/pdd_format_notes/FEATURE_NAME.md` 中追加:
- 参数名 → PDD key 映射
- 取值范围 / 类型 (int, bool, enum, string)
- 默认值
- 依赖关系 (如 "仅 ACE-Lite 有效")
- 数学公式 (如 interleave mask 计算)

---

## Phase 3: 实现 + 测试 + 经验记录 (Per-Feature)

### 目标
对每个已逆向出 PDD 格式的 feature，在 DSL 中实现、端到端验证、记录经验。

### Task 3.1: Stage 4 — DSL 实现 (模板)

**Files (根据 feature 类型选择):**
- Modify: `flexnoc_dsl/protocol.py` — 新协议或协议参数
- Modify: `flexnoc_dsl/socket.py` — Socket 级参数 (conversion, performance)
- Modify: `flexnoc_dsl/port.py` — 端口/标志
- Modify: `flexnoc_dsl/switch.py` — 拓扑元素 (firewall, tunnel, arbiter)
- Modify: `flexnoc_dsl/architecture.py` — 架构级自动派生逻辑
- Modify: `flexnoc_dsl/pdd_writer.py` — XML 输出
- Modify: `flexnoc_dsl/project.py` — NocProject 顶层接口
- Modify: `flexnoc_dsl/__init__.py` — 导出
- Create: `flexnoc_dsl/NEWMODULE.py` — 新增模块 (如 power.py, firewall.py)

**Step 1: 设计 API (在 project.py 中添加方法)**

遵循现有 DSL 风格:
```python
# 用户面 API 示例
noc.add_FEATURE(name, param1=default1, param2=default2)
```

设计原则:
- Specification-only: 用户只描述意图
- Architecture 自动派生: auto_derive() 处理
- 参数命名与 FlexNoC 文档一致 (但用 snake_case)
- 提供合理默认值

**Step 2: 添加 dataclass (在对应模块中)**

```python
@dataclass
class NewFeature:
    name: str
    param1: type = default
    param2: type = default
```

**Step 3: 添加 PDD XML 输出 (在 pdd_writer.py 中)**

在 `PddWriter._write_SECTION()` 方法中添加输出逻辑。
关键: 必须同时处理 spec/arch/struct 三个 phase 的输出。

**Step 4: 更新 NocProject._finalize()**

如果新 feature 需要自动计算（如 interleave mask），在 `_finalize()` 中添加。

---

### Task 3.2: Stage 5 — 端到端验证 (模板)

**Files:**
- Create: `examples/test_FEATURE.py` — 最小示例

**Step 1: 写最小测试用例**

```python
from flexnoc_dsl import NocProject, AXI

noc = NocProject("test_FEATURE")
axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64, id=4))
clk = noc.add_clock("clk_domain", freq="500MHz")

# 添加最小拓扑
noc.add_initiator("init_0", protocol=axi, clock=clk)
noc.add_target("targ_0", protocol=axi, clock=clk, base=0x0, size="256M")
noc.connect_all()

# 添加待测试的 feature
noc.add_FEATURE(...)

noc.set_export("Verilog", simulator="VCS")
noc.write_pdd("test_FEATURE.pdd")
```

**Step 2: 生成 PDD 并检查 XML**

```bash
cd ~/flexnoc-work/noc2pdd/examples
unset PYTHONHOME && unset PYTHONPATH
python3 test_FEATURE.py
# 检查生成的 XML 是否包含预期的 entry
grep -A5 "EXPECTED_KEY" test_FEATURE.pdd
```

Expected: XML 中出现正确的 key/value 结构

**Step 3: FlexNoC 端到端 — exportVerilog**

```bash
docker run --rm --hostname YunqiLaptop --cap-add NET_ADMIN --entrypoint bash \
  -v ~/flexnoc-work:/work flexnoc:5.3.0-standalone -c '
ip link set eth0 down; ip link set eth0 name xp0; ip link set xp0 address 00:21:5a:45:ac:60; ip link set xp0 up
cd /opt/arteris/License && rm -f run/*.pid && bash arteris start 2>/dev/null && sleep 5
Xvfb :99 -screen 0 1024x768x24 & sleep 2; export DISPLAY=:99
source /opt/flexnoc/5.3.0/etc/bashrc
export LD_LIBRARY_PATH="/opt/flexnoc/5.3.0/TopologyEditor/lib:$LD_LIBRARY_PATH"
FlexNoC -d False -p /work/noc2pdd/examples/test_FEATURE.pdd exportVerilog \
  -s test_FEATURE_struct -c exports.Vlog -o /work/output_FEATURE 2>&1
echo "Exit: $?"
ls /work/output_FEATURE/*.v 2>/dev/null | wc -l
'
```

Expected: Exit code 0, Verilog 文件生成

**Step 4: (可选) 验证 Memory Map**

```bash
# 同一 Docker 容器内
FlexNoC -d False -p /work/noc2pdd/examples/test_FEATURE.pdd exportAMemoryMap \
  -s test_FEATURE_struct -o /work/output_FEATURE/memmap.csv 2>&1
cat /work/output_FEATURE/memmap.csv
```

---

### Task 3.3: 经验记录 (Per-Feature)

**Files:**
- Create/Modify: `docs/pdd_format_notes/FEATURE_NAME.md`
- Modify: `API_REFERENCE.md` — Section 9 & 10 更新

**每个 feature 完成后，记录以下内容:**

```markdown
# FEATURE_NAME PDD 格式笔记

## 发现过程
- 从哪个数据源找到 (D1-D6)
- 关键搜索词
- 遇到的坑

## PDD XML 结构
```xml
<具体 XML 片段>
```

## 参数映射表
| PDD key | DSL 参数 | 类型 | 范围 | 默认值 |
|---------|---------|------|------|--------|

## 验证结果
- Verilog 导出: ✅/❌
- 行数变化: 从 N 行 → M 行
- 特殊注意事项

## 教训 / Gotcha
- (记录任何非直觉的行为)
```

**更新 API_REFERENCE.md:**
- Section 9: 将 feature 从 ❌ 改为 ✅
- Section 4: 添加 API 使用文档
- Section 10: 从 "不支持" 列表移除

---

## Phase 4: 完整性迭代检查

### 目标
交叉验证 feature_checklist 是否有遗漏。发现缺失则回到 Phase 1。

### Task 4.1: 数据源交叉验证

**Step 1: PDD key 覆盖率检查**

```bash
# 提取参考 PDD 中所有 key
docker run --rm -v ~/flexnoc-work:/work --entrypoint bash flexnoc:5.3.0-standalone -c '
grep -oP "key=\"[^\"]+\"" /work/PSI_reference_design.pdd | sort -u | sed "s/key=\"//;s/\"//"
' > /tmp/all_pdd_keys.txt

# 对比 checklist 中已记录的 key
grep -oP "\`[a-zA-Z_]+\`" docs/feature_checklist.md | sort -u > /tmp/checklist_keys.txt
comm -23 /tmp/all_pdd_keys.txt /tmp/checklist_keys.txt
```

Expected: 空输出 (无遗漏)。若有输出，回到 Phase 1 补充。

**Step 2: TOC 类别覆盖率检查**

对照 TOC 大章节标题，逐个确认 checklist 中已有对应 feature 条目:

```
□ Addressing and Security
□ Clocking and Reset
□ Memory Units
□ NIU Transaction Handling (Generic)
□ NIU Transaction Handling (AXI/AHB/APB/NSP/OCP/PIF)
□ Observability
□ Power Management
□ QoS
□ Run-time Configuration (Service Network)
□ Resilience
□ Physical Implementation (FloorPlanner)
□ FlexArtist Export Options
□ Design Composition
□ FlexExplorer (Scenario/Queue/TargetModel)
```

**Step 3: Object kind 覆盖率检查**

确保 33 种 PDD object kind 中，每种都在 checklist 的某个 feature 下有记录:

```
clock, clockManager, clockRegime, dtpLink, dtpSwitch,
exportOption, flow, folder, initiator, mapping,
modeFlag, obsSwitch, observer, port, procedure,
process, project, protocol, queue, scenario,
socket, specification, srvSwitch, swModule,
switchBasedArchitecture, switchBasedStructure,
target, targetModel,
activityZone, power, swbNet, userFlag, voltage
```

---

### Task 4.2: 差分验证 — 新 PDD 生成 vs 参考 PDD

**Step 1: 生成一个与 sampleproject 功能等价的 DSL 脚本**

当 DSL 覆盖足够多 feature 后，尝试用 DSL 复现 sampleproject.pdd 的配置。

**Step 2: XML diff 比较**

```bash
# 规范化 XML 后 diff
python3 -c "
import xml.dom.minidom as md
for f in ['generated.pdd', 'sampleproject.pdd']:
    with open(f) as fh:
        doc = md.parseString(fh.read())
    with open(f'{f}.norm', 'w') as out:
        out.write(doc.toprettyxml())
"
diff generated.pdd.norm sampleproject.pdd.norm | head -100
```

发现差异的每个 entry key / object kind 即为潜在遗漏 feature → 回到 Phase 1。

---

### Task 4.3: 迭代循环判定

```
IF 所有数据源覆盖率 = 100%
   AND sampleproject.pdd 差分 < 5 个非关键差异
   AND PSI_reference_design.pdd 主要 feature 已覆盖
THEN → 完成
ELSE → 回到 Phase 1, 补充未覆盖的 feature
```

每轮迭代后更新 `docs/feature_checklist.md` 顶部的进度统计:

```markdown
## 进度
- 总 feature 数: N
- ✅ 已实现并验证: X
- 🔧 已实现未验证: Y
- ❌ 未实现: Z
- ⬜ 不适用: W
- 覆盖率: (X+Y)/N = ??%
```

---

## Feature 优先级排序 (建议执行顺序)

基于 SoC 设计实际需求和实现复杂度排序:

### P0 — 核心功能 (必须实现)

| # | Feature | 理由 | 预计复杂度 |
|---|---------|------|-----------|
| 1 | **Firewall** | SoC 安全隔离必需，多数设计必用 | 中 — 新 object kind + routing |
| 2 | **AXI4/AXI5 扩展参数** | wLen, wQos, wRegion, AMBA5 | 低 — 扩展现有 AXI() |
| 3 | **UserFlag** | secure/privileged/debug 信号映射 | 低 — 新 dataclass + PDD 输出 |
| 4 | **自定义仲裁** | PRIORITY/RR/ROTATE/FIFO | 低 — architecture 层参数 |
| 5 | **Pipeline Stages** | inputPipes/outputPipes 配置 | 低 — architecture 层参数 |
| 6 | **自定义 userMapping** | 非 CONST_0 映射规则 | 低 — 扩展现有逻辑 |

### P1 — 常用功能

| # | Feature | 理由 | 预计复杂度 |
|---|---------|------|-----------|
| 7 | **ACE-Lite 协议** | cache-coherent 设计必需 | 中 — 新协议 + DVM 拓扑 |
| 8 | **AHB 协议** | 低速外设接口常用 | 低 — 新工厂函数 |
| 9 | **AXI-Lite 协议** | 寄存器访问接口 | 低 — 新工厂函数 |
| 10 | **Clock Gating 细粒度** | unit-level/register-level 选择 | 低 — clock 参数扩展 |
| 11 | **Clock Adapter (async/meso)** | 多时钟域参数精细控制 | 中 — architecture 层 |
| 12 | **Power Domain** | power/voltage/activityZone | 中 — 新模块 power.py |
| 13 | **Export Options 完整** | 多导出格式, customerCells | 中 — 扩展 pdd_writer |
| 14 | **QoS Generator** | fixed/limiter/regulator 模式 | 中 — 新 dataclass |
| 15 | **Service Network** | 寄存器访问网络自定义 | 中 — srvSwitch 参数 |

### P2 — 高级功能

| # | Feature | 理由 | 预计复杂度 |
|---|---------|------|-----------|
| 16 | **Observer 完整配置** | 探针/过滤器/统计/ATB | 高 — 多级嵌套 XML |
| 17 | **Resilience** | ECC/parity/packet protection | 高 — 多个新参数组 |
| 18 | **Tunnel / VC-Link** | 长距离传输优化 | 高 — 新拓扑对象 |
| 19 | **NSP 协议** | NoC-to-NoC socket | 高 — 全新协议栈 |
| 20 | **Serialization** | 带宽转换适配 | 中 — architecture 层 |
| 21 | **Register File Memory** | 外部 SRAM 替代 FIFO | 中 — buffering 参数 |
| 22 | **Multi-port NIU** | 多端口合并 | 高 — 新拓扑模式 |
| 23 | **Scenario/Queue/TargetModel** | 仿真探索 | 中 — 新模块 scenario.py |

### P3 — 边缘功能

| # | Feature | 理由 | 预计复杂度 |
|---|---------|------|-----------|
| 24 | **PIF 协议** | Xtensa 专用，极少使用 | 中 |
| 25 | **OCP 完整参数** | OCP 渐废弃 | 低 |
| 26 | **NSP_BROADCAST** | 特殊广播场景 | 中 |
| 27 | **FloorPlanner 参数** | 物理实现辅助 | 高 |
| 28 | **Design Composition** | 多 NoC 组合 | 高 |
| 29 | **SystemC/IP-XACT 导出** | 非 Verilog 输出 | 中 |
| 30 | **Power Intent (UPF/CPF)** | 自动生成 | 高 |

---

## 附录 A: FlexNoC 文档 TOC Feature 分类映射

> 从 3,519 行 TOC 中提取的主要功能模块 → DSL coverage 状态

| TOC 章节 | 子主题 | DSL 状态 |
|----------|--------|----------|
| **Addressing and Security** | compact/striped mappings | ✅ 基础 mapping |
| | address interleaving | ✅ 已实现 |
| | firewall | ❌ |
| | security labels/flags | ❌ |
| | transaction-level security | ❌ |
| **Clocking and Reset** | clock domains | ✅ |
| | clock gating (unit/register) | 🔧 基础 |
| | clock manager, generated clocks | ❌ |
| | clock adapters (async/mesochronous) | 🔧 自动 CDC |
| | customer cells (SynchronizerCell, GaterCell) | ❌ |
| **Memory Units** | DDR subsystems | ❌ |
| | multi-channel, interleaved memory | ✅ 地址交织 |
| | DRAM address mapping, scheduler | ❌ |
| **NIU — Generic** | narrow burst packing, splitting | ❌ |
| | endianness (useBigEndian) | ❌ |
| | posted writes, early write response | ❌ |
| | atomic/exclusive access | ❌ |
| | error codes (useErrorCodes) | ❌ |
| | minInterleaveSize | ✅ |
| | wSeqId, nPendingTrans | ✅ |
| | QoS (hurry/pressure/urgency) | 🔧 urgency only |
| | reorder buffer | ❌ |
| | pipeline stages | ❌ |
| | time-out (watchdog) | ❌ |
| **NIU — AXI/ACE-Lite** | AXI spec params | ✅ 基础 |
| | ACE-Lite (barrier, DVM, early WrRsp) | ❌ |
| | AXI conversion params | ❌ |
| | AXI performance params | ❌ |
| **NIU — AXI-Lite** | protocol + NIU | ❌ |
| **NIU — AHB** | protocol + NIU | ❌ |
| **NIU — APB** | protocol + NIU | 🔧 协议定义 |
| **NIU — OCP** | protocol + NIU | 🔧 协议定义 |
| **NIU — NSP** | protocol + NIU | ❌ |
| **NIU — PIF** | protocol + NIU | ❌ |
| **Observability** | observers, probes, error logging | 🔧 基础 observer |
| | packet/transaction probes | ❌ |
| | statistics, profiling | ❌ |
| | ATB formatting, STPv2 | ❌ |
| | universal probes | ❌ |
| **Power Management** | power/voltage domains | ❌ |
| | socket/transport disconnect | ❌ |
| | PMU interface | ❌ |
| | activity zones | ❌ |
| | power intent (UPF/CPF) | ❌ |
| **QoS** | urgency levels | ✅ |
| | QoS generators (fixed/limiter/regulator) | ❌ |
| | arbitration algorithms | ❌ |
| | buffering params | ❌ |
| | VC-Link tunnels | ❌ |
| | rate adapters | ❌ |
| **Service Network** | service topology | ❌ |
| | register configuration | ❌ |
| | sideband managers | ❌ |
| **Resilience** | port protection (parity/ECC) | ❌ |
| | packet protection | ❌ |
| | unit duplication | ❌ |
| | fault aggregation | ❌ |
| | data info support | ❌ |
| **Physical Implementation** | synthesis directives | ❌ |
| | FloorPlanner | ❌ |
| | technology file | ❌ |
| **Export Options** | Verilog customization | ✅ 基础 |
| | customerCells | ❌ |
| | SystemC | ❌ |
| | IP-XACT | ❌ |
| | Register Map | ❌ |
| | UVM export | ❌ |
| **Design Composition** | multi-NoC connections | ❌ |
| **Exploration** | scenarios, queues, target models | ❌ |

---

## 附录 B: 具体执行 — 第一轮迭代任务列表

以下是 Phase 1→2→3 的第一轮具体执行步骤 (P0 feature):

### Iteration 1, Feature 1: Firewall

1. `grep -i "firewall\|security" sampleproject.pdd PSI_reference_design.pdd`
2. 提取 firewall XML 结构 (object kind, parent, entries)
3. 搜索 TOC 中 "Firewall" 相关页面 (9079.htm 等)
4. 阅读 firewall 配置参数 (securityFlags, securityZone, etc.)
5. 在 `flexnoc_dsl/` 中实现 (可能需要新 firewall.py)
6. 写 `examples/test_firewall.py`
7. Docker 端到端验证
8. 记录 `docs/pdd_format_notes/firewall.md`
9. 更新 `API_REFERENCE.md`

### Iteration 1, Feature 2: AXI4/AXI5 扩展参数

1. `grep -i "wLen\|wQos\|wRegion\|AMBA5\|useAtomic\|useUniqueId" PSI_reference_design.pdd`
2. 在 TOC 中找 "AXI and ACE-Lite common parameters" 页面
3. 列出所有 AXI 扩展参数及默认值
4. 扩展 `AXI()` 工厂函数和 Protocol dataclass
5. 扩展 pdd_writer 输出
6. 写 `examples/test_axi_extended.py`
7. Docker 端到端验证
8. 记录经验

### Iteration 1, Feature 3: UserFlag

1. `grep -i "userFlag\|userFlags\|securityFlag" PSI_reference_design.pdd`
2. 提取 userFlag XML 结构
3. 阅读 TOC "Flags page" 和 "User page" 参数
4. 实现 UserFlag dataclass + PDD 输出
5. 写测试
6. 验证

### Iteration 1, Feature 4: 自定义仲裁策略

1. `grep -i "arbiter\|ArbiterMode\|ROTATE\|PRIORITY\|FIFO" sampleproject.pdd PSI_reference_design.pdd`
2. 阅读 TOC "QoS arbitration" (FIFO, Rotate, Round Robin per urgency)
3. 找到 architecture 层 arbiter 参数结构
4. 扩展 DtpSwitch 或新 dataclass
5. 写测试
6. 验证

### Iteration 1, Feature 5: Pipeline Stages

1. `grep -i "inputPipes\|outputPipes\|pipe\|autopipe" sampleproject.pdd`
2. 阅读 TOC "Pipeline stage parameters" 各 NIU 类型
3. 在 architecture 层添加 pipe 配置参数
4. 写测试
5. 验证

### Iteration 1, Feature 6: 自定义 userMapping

1. 分析现有 AXI userMapping (ARCache, AWCache, Prot → CONST_0)
2. 在 TOC 中搜索 "userMapping" "reqUserAlias" "rspUserMap"
3. 实现用户可配置 mapping 规则
4. 写测试
5. 验证

---

## 执行策略

**推荐执行方式: Subagent-Driven**
- 每个 feature 作为一个独立子任务
- 每完成一个 feature 后 review 结果
- 发现新 feature 时实时更新 checklist

**节奏:**
- 每轮迭代目标: 完成 4-6 个 feature
- 每个 P0 feature: Stages 1-5 全流程
- 每个 P1/P2 feature: 可以 batch Stage 1-2 (并行调研)，然后逐个 Stage 3-5

**完成标准:**
- `docs/feature_checklist.md` 中 ❌ 数量 < 5 (仅剩 P3 边缘功能)
- 所有 P0 + P1 feature 端到端验证通过
- `API_REFERENCE.md` 覆盖所有已实现 feature
- 参考 PDD diff 差异 < 10 个非关键条目
