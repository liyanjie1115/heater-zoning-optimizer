# Heater Zoning Optimizer

用于分析加热区沿长度方向的温度剖面，并在模块长度、模块间距、边缘外伸余量等安装约束下，对比两类分区方案：

- 等距分区
- 按模块节距对齐的最优分区

项目现在包含三种入口：

- 桌面 GUI
- CLI
- 可选网页入口

桌面 GUI 是主入口。

## 项目结构

```text
heater-zoning-optimizer/
├─ desktop_app.py              # 桌面 GUI 入口
├─ cli.py                      # 命令行入口
├─ app.py                      # 可选网页入口
├─ src/heater_zoning/
│  ├─ analysis.py              # 核心算法
│  ├─ config.py                # 参数模型
│  ├─ exporters.py             # Excel 导出
│  ├─ gui.py                   # Tkinter 桌面界面
│  ├─ io_utils.py              # 输入解析
│  ├─ reporting.py             # 报表数据整理
│  ├─ runflow.py               # 统一执行流程
│  └─ visualization.py         # Plotly / Matplotlib 图表
├─ data/                       # 示例输入
├─ outputs/                    # 分析输出
├─ legacy/                     # 原始脚本和历史 Excel
├─ tests/                      # 自动化测试
└─ RELEASE.md                  # 发布说明
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

## 主要能力

- 上传或使用示例温度剖面
- 配置分区和模块安装约束
- 生成等距分区与模块对齐分区
- 显示温度分区图、模块布局图、指标柱状图、雷达图
- 在图中显示每个分区的虚线边界
- 导出美化后的 Excel 报告

## 测试

```bash
python -m unittest discover -s tests -v
```

## 发布

发布相关说明见 [RELEASE.md](RELEASE.md)。
