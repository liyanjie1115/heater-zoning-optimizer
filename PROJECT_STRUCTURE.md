# 项目结构说明

这个项目当前是一个“加热分区分析工具”，主入口是桌面版，同时保留了 CLI 和网页版本。

## 根目录

- `desktop_app.py`
  - 桌面 GUI 启动入口
  - 启动后打开 Qt 桌面窗口

- `cli.py`
  - 命令行入口
  - 适合批量执行、脚本集成和快速导出 Excel

- `app.py`
  - 可选网页入口
  - 启动 Flask 页面，在浏览器里查看结果

- `README.md`
  - 项目使用说明

- `RELEASE.md`
  - 发布和打包说明

- `PROJECT_STRUCTURE.md`
  - 当前这份结构说明文件

- `requirements.txt`
  - 项目依赖列表

- `heater_zoning_optimizer.spec`
  - PyInstaller 打包配置

- `.gitignore`
  - Git 忽略规则

## 核心源码

### `src/heater_zoning/`

- `__init__.py`
  - 对外暴露常用入口

- `analysis.py`
  - 核心分析算法
  - 包括：
    - 等距分区
    - 模块对齐最优分区
    - 模块排布计算
    - 评分和推荐逻辑
    - 三点采样计算

- `config.py`
  - 分析参数模型
  - 统一管理：
    - 基础尺寸参数
    - 三点采样位置比例
    - 评分权重
    - 衰减和惩罚项

- `io_utils.py`
  - 输入数据读取和规范化
  - 支持 CSV / Excel
  - 兼容中英文列名

- `models.py`
  - 数据模型定义
  - 包括：
    - 单个分区结果
    - 评价指标
    - 总分析结果

- `reporting.py`
  - 报表整理层
  - 把分析结果转换成 GUI、Excel、PDF 可复用的数据表

- `runflow.py`
  - 统一执行流程
  - 串起：
    - 加载输入
    - 运行分析
    - 生成报表
    - 导出文件

- `exporters.py`
  - 导出层
  - 负责：
    - Excel 导出
    - Excel 美化
    - PDF 摘要导出

- `visualization.py`
  - 图表层
  - 负责：
    - Plotly 网页图表
    - Matplotlib 桌面/PDF 图表
    - 温度图
    - 模块排布图
    - 指标对比图
    - 雷达图

- `gui.py`
  - 桌面界面实现
  - 当前使用 `PySide6 + matplotlib`
  - 包括：
    - 文件选择
    - 参数编辑
    - 参数模板
    - 图表展示
    - 表格展示
    - Excel / PDF 导出

- `cli.py`
  - CLI 具体实现
  - 解析命令行参数并调用统一分析流程

- `settings.py`
  - 桌面端本地设置持久化
  - 保存：
    - 最近文件
    - 参数模板

- `sample_data.py`
  - 内置示例数据

- `fonts.py`
  - Matplotlib 中文字体配置

## 其他目录

### `data/`

- 示例输入数据目录

### `outputs/`

- 运行输出目录
- 存放：
  - Excel 报告
  - PDF 摘要

### `tests/`

- 自动化测试目录
- 当前覆盖：
  - 核心分析
  - 输入规范化
  - Excel 导出
  - PDF 导出
  - CLI
  - 设置持久化

### `scripts/`

- 辅助脚本目录
- 包括 Windows 打包脚本

### `legacy/`

- 历史文件目录
- 用于保留旧实现或旧输出结果

### `templates/`

- Flask 网页模板目录

### `static/`

- Flask 静态资源目录

## 当前推荐启动方式

### 桌面版

```bash
python desktop_app.py
```

### 命令行

```bash
python cli.py --json
```

### 网页版

```bash
python app.py
```
