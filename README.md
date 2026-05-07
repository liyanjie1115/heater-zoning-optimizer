# Heater Zoning Optimizer

用于分析加热区沿长度方向的温度剖面，并在模块长度、模块间距、边缘外伸余量等安装约束下，对比两类分区方案：

- 等距分区
- 按模块节距对齐的最优分区

项目已经重构为适合 GitHub 管理的应用结构，包含输入、执行、后处理和本地网页界面。

## 项目结构

```text
heater-zoning-optimizer/
├─ app.py                     # Flask Web 入口
├─ src/heater_zoning/         # 核心算法、IO、导出、可视化
├─ templates/                # HTML 模板
├─ static/                   # 样式资源
├─ data/                     # 示例输入数据
├─ outputs/                  # 导出的 Excel 报告
├─ tests/                    # 基础测试
└─ legacy/                   # 原始脚本和历史 Excel 输出
```

## 输入格式

支持 `CSV` / `Excel` 文件，至少包含两列：

- `distance_mm`
- `temperature_c`

也兼容这些常见列名：

- `distance` / `x` / `距离`
- `temperature` / `temp` / `温度`

要求：

- 距离列严格递增
- 第一行从 `0 mm` 开始
- 最后一行覆盖总长度

## 运行

```bash
python app.py
```

启动后访问：

```text
http://127.0.0.1:5000
```

## 主要能力

- 上传或使用示例温度剖面
- 配置分区与模块约束参数
- 生成两类分区方案
- 查看温度分区图、模块布局图、指标对比图、雷达图
- 导出美化后的 Excel 报告

## 测试

```bash
python -m unittest discover -s tests
```

## 说明

- 原始脚本已移动到 `legacy/`
- 当前界面为本地单用户分析台，适合个人研究和方案比较

