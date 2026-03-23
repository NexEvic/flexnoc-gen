# Docker E2E 测试指南

> 使用 Docker 化的 FlexNoC 5.3.0 进行端到端验证

---

## 1. 环境要求

| 组件 | 要求 | 说明 |
|------|------|------|
| Docker | 已安装 | `docker run` 可用 |
| 镜像 | `flexnoc:5.3.0-standalone` | 包含 FlexNoC + License Server + Xvfb |
| 网络 | `--cap-add NET_ADMIN` | MAC 地址伪装所需 |
| 挂载 | `-v ~/flexnoc-work:/work` | PDD 文件 + 输出目录 |

## 2. Docker 命令模板

### 2.1 完整命令

```bash
docker run --rm \
  --hostname YunqiLaptop \
  --cap-add NET_ADMIN \
  --entrypoint bash \
  -v ~/flexnoc-work:/work \
  flexnoc:5.3.0-standalone \
  -c '
    # 1. MAC 地址伪装 (License 绑定)
    ip link set eth0 down
    ip link set eth0 name xp0
    ip link set xp0 address 00:21:5a:45:ac:60
    ip link set xp0 up

    # 2. 启动 License Server
    cd /opt/arteris/License && rm -f run/*.pid && bash arteris start 2>/dev/null && sleep 5

    # 3. 启动虚拟显示 (FlexNoC GUI 依赖)
    Xvfb :99 -screen 0 1024x768x24 & sleep 2
    export DISPLAY=:99

    # 4. 加载 FlexNoC 环境
    source /opt/flexnoc/5.3.0/etc/bashrc
    export LD_LIBRARY_PATH="/opt/flexnoc/5.3.0/TopologyEditor/lib:$LD_LIBRARY_PATH"

    # 5. 执行导出
    FlexNoC -d False -p /work/INPUT.pdd exportVerilog \
      -s STRUCT_NAME -c EXPORT_NAME -o /work/OUTPUT_DIR
  '
```

### 2.2 关键参数说明

| 参数 | 含义 | 注意事项 |
|------|------|---------|
| `--hostname YunqiLaptop` | 主识名，License 检查用 | 必须匹配 License 配置 |
| `--cap-add NET_ADMIN` | 允许修改网络设备 | MAC 伪装必需 |
| `--entrypoint bash` | 覆盖默认 entrypoint | 允许执行自定义脚本 |
| `-v ~/flexnoc-work:/work` | 挂载工作目录 | PDD 和输出都在此目录 |
| `-d False` | 禁用 GUI/设计验证 | 允许 CLI 批处理模式 |
| `-p /work/INPUT.pdd` | PDD 文件路径 | 容器内路径 |
| `-s STRUCT_NAME` | structure 名 | = `{project_name}_struct` |
| `-c EXPORT_NAME` | export option 名 | = `set_export()` 的 name |
| `-o /work/OUTPUT_DIR` | 输出目录 | 容器内路径 |

## 3. Python 脚本生成 + Docker 执行

标准的 E2E 测试流程:

```python
import subprocess, tempfile, os

from flexnoc_dsl import NocProject, AXI

# Step 1: 生成 PDD
noc = NocProject("test_noc")
axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64))
clk = noc.add_clock("clk", freq="500MHz")
noc.add_initiator("cpu", protocol=axi, clock=clk)
noc.add_target("mem", protocol=axi, clock=clk, base=0x0, size="1G")
noc.connect_all()
noc.set_export("Verilog", simulator="VCS")
noc.write_pdd("/home/user/flexnoc-work/test_noc.pdd")

# Step 2: 构建 Docker 命令
cmd = noc.get_export_command("/work/test_noc.pdd", "/work/test_output")
docker_cmd = f"""docker run --rm \\
  --hostname YunqiLaptop \\
  --cap-add NET_ADMIN \\
  --entrypoint bash \\
  -v ~/flexnoc-work:/work \\
  flexnoc:5.3.0-standalone \\
  -c '
    ip link set eth0 down; ip link set eth0 name xp0;
    ip link set xp0 address 00:21:5a:45:ac:60; ip link set xp0 up;
    cd /opt/arteris/License && rm -f run/*.pid && bash arteris start 2>/dev/null && sleep 5;
    Xvfb :99 -screen 0 1024x768x24 & sleep 2;
    export DISPLAY=:99;
    source /opt/flexnoc/5.3.0/etc/bashrc;
    export LD_LIBRARY_PATH="/opt/flexnoc/5.3.0/TopologyEditor/lib:$LD_LIBRARY_PATH";
    {cmd}
  '"""

# Step 3: 执行
result = subprocess.run(docker_cmd, shell=True, capture_output=True, text=True)
assert result.returncode == 0, f"FlexNoC export failed: {result.stderr}"

# Step 4: 验证输出
assert os.path.exists(os.path.expanduser("~/flexnoc-work/test_output/test_noc_struct.v"))
```

## 4. FlexNoC CLI 参数详解

### 4.1 exportVerilog 子命令

```
FlexNoC -d False -p <PDD> exportVerilog -s <STRUCT> -c <EXPORT> -o <DIR>
```

| 参数 | 说明 |
|------|------|
| `-d False` | Disable design (让 FlexNoC 自动推导 architecture/structure 层) |
| `-p <PDD>` | PDD 文件路径 |
| `exportVerilog` | 导出 Verilog RTL |
| `-s <STRUCT>` | Structure 名 (自动命名: `{project}_struct`) |
| `-c <EXPORT>` | Export option 名 (如 `exports.Vlog`) |
| `-o <DIR>` | 输出目录 |

### 4.2 输出文件

典型导出输出:

| 文件 | 说明 |
|------|------|
| `{struct}_struct.v` | 主结构文件 (top-level) |
| `{struct}_struct_commons.v` | 公共模块 |
| `rtl.ClockManagerCell.v` | 时钟管理 cell |
| `rtl.GaterCell.v` | 时钟门控 cell |
| `rtl.SynchronizerCell.v` | CDC 同步器 cell (多时钟域才生成) |
| `synthesisFileNames.txt` | 综合文件列表 |
| `simulationFileNames.txt` | 仿真文件列表 |
| `CustomerCellsInfo` | 客户 cell 信息 |

## 5. 常见错误及排查

| 错误 | 原因 | 解决 |
|------|------|------|
| `SIGSEGV` / Exit 139 | PDD 结构错误 | 检查 PDD XML 语法 |
| `License check failed` | MAC/hostname 不匹配 | 检查 --hostname 和 MAC |
| `Cannot open display` | Xvfb 未启动 | 确保 Xvfb 启动并 DISPLAY 设置 |
| `No such file` | 路径不在挂载目录 | 确保用 /work/ 容器内路径 |
| Exit 0 但无文件 | struct/export 名不匹配 | 对照 PDD 中的 name 检查 -s -c 参数 |

## 6. pytest 集成

使用 `@pytest.mark.docker` 标记 E2E 测试:

```python
@pytest.mark.docker
def test_basic_export(docker_runner, tmp_path):
    noc = NocProject("test")
    # ... 配置 ...
    pdd_path = str(tmp_path / "test.pdd")
    noc.write_pdd(pdd_path)
    result = docker_runner(pdd_path, "test_struct", "exports.Vlog")
    assert result.returncode == 0
```

`docker_runner` fixture 封装了完整的 Docker 命令构建逻辑，
详见 `tests/conftest.py`。

## 7. 超时与性能

| 配置类型 | 典型耗时 | 建议超时 |
|---------|---------|---------|
| 简单 2x2 | 30-60s | 120s |
| 混合协议 3x4 | 60-120s | 180s |
| 复杂 QoS + 电源 | 60-180s | 300s |

主要耗时在:
1. License Server 启动 (~5s)
2. Xvfb 启动 (~2s)
3. FlexNoC elaboration + export (主要变量)
