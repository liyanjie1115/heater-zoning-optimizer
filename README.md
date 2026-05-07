# Heater Zoning Optimizer

用于分析加热区沿长度方向的温度剖面，并在模块长度、模块间距、边缘外伸余量等安装约束下，对比两类分区方案：

- 等距分区
- 按模块节距对齐的最优分区

项目当前提供三种入口：

- 桌面 GUI
- CLI
- 可选网页入口

桌面 GUI 是主入口。

## 项目结构

```text
heater-zoning-optimizer/
├─ desktop_app.py                  # 桌面 GUI 入口
├─ cli.py                          # 命令行入口
├─ app.py                          # 可选网页入口
├─ heater_zoning_optimizer.spec    # PyInstaller spec
├─ scripts/
│  ├─ build_windows.ps1            # Windows 打包脚本
│  └─ build_windows.bat
├─ src/heater_zoning/
│  ├─ analysis.py                  # 核心算法
│  ├─ cli.py                       # CLI 实现
│  ├─ config.py                    # 参数模型
│  ├─ exporters.py                 # Excel / PDF 导出
│  ├─ gui.py                       # Tkinter 桌面界面
│  ├─ io_utils.py                  # 输入解析
│  ├─ reporting.py                 # 报表数据整理
│  ├─ runflow.py                   # 统一执行流程
│  ├─ settings.py                  # 最近文件 / 参数模板
│  └─ visualization.py             # Plotly / Matplotlib 图表
├─ data/
├─ outputs/
├─ legacy/
├─ tests/
└─ RELEASE.md
```

## 输入格式

支持 `CSV` / `Excel` 文件，至少包含两列：

- `distance_mm`
- `temperature_c`

也兼容这些列名：

- `distance` / `x` / `距离`
- `temperature` / `temp` / `温度`

要求：

- 距离列严格递增
- 第一行从 `0 mm` 开始
- 最后一行覆盖总长度

## 桌面端能力

- 示例数据 / 本地文件两种输入方式
- 最近文件列表
- 参数模板保存与加载
- 温度分区图、模块布局图、指标柱状图、雷达图
- 图中显示每个分区的虚线边界
- Excel 报告导出
- PDF 摘要一键导出

## 运行

### 桌面界面

```bash
python desktop_app.py
```

### CLI

```bash
python cli.py --help
```

示例：

```bash
python cli.py --json
python cli.py --input data/sample_profile.csv --output-name sample_report.xlsx
```

### 可选网页界面

```bash
python app.py
```

然后访问：

```text
http://127.0.0.1:5000
```

## 测试

```bash
python -m unittest discover -s tests -v
```

## Windows 打包

```powershell
.\scripts\build_windows.ps1
```

或：

```bat
scripts\build_windows.bat
```

更多说明见 [RELEASE.md](RELEASE.md)。
